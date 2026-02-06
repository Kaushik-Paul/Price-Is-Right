import os
from agents.deals import Opportunity
from agents.agent import Agent
from litellm import completion
from mailjet_rest import Client


class MessagingAgent(Agent):
    name = "Messaging Agent"
    color = Agent.WHITE
    MODEL = "openrouter/xiaomi/mimo-v2-flash"

    def __init__(self):
        """
        Set up this object to send email notifications via Mailjet
        """
        self.log("Messaging Agent is initializing")
        self.api_key = os.getenv("MAILJET_API_KEY")
        self.api_secret = os.getenv("MAILJET_API_SECRET")
        self.from_email = os.getenv("MAILJET_FROM_EMAIL")
        self.to_email = os.getenv("MAILJET_TO_EMAIL")
        self.mailjet = Client(auth=(self.api_key, self.api_secret), version='v3.1')
        self.log("Messaging Agent has initialized Mailjet and LLM")

    def send_email(self, text: str, subject: str = "Deal Alert!", to_email: str = None):
        """
        Send an email notification using the Mailjet API
        
        Args:
            text: The email body text
            subject: Email subject line
            to_email: Optional recipient email. Uses environment variable if not provided.
        """
        recipient_email = to_email or self.to_email
        self.log(f"Messaging Agent is sending an email notification to {recipient_email}")
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": self.from_email,
                        "Name": "Deal Finder Agent"
                    },
                    "To": [
                        {
                            "Email": recipient_email,
                            "Name": "Deal Subscriber"
                        }
                    ],
                    "Subject": subject,
                    "TextPart": text,
                }
            ]
        }
        result = self.mailjet.send.create(data=data)
        return result.json()

    def alert(self, opportunity: Opportunity, to_email: str = None):
        """
        Make an alert about the specified Opportunity
        
        Args:
            opportunity: The deal opportunity to alert about
            to_email: Optional recipient email. Uses environment variable if not provided.
        """
        text = "🎉 Deal Alert!\n\n"
        text += f"💰 Price: ${opportunity.deal.price:.2f}\n"
        text += f"📊 Estimated Value: ${opportunity.estimate:.2f}\n"
        text += f"🏷️ Discount: ${opportunity.discount:.2f}\n\n"
        text += f"📦 Product: {opportunity.deal.product_description}\n\n"
        text += f"🔗 Link: {opportunity.deal.url}\n"
        self.send_email(text, to_email=to_email)
        self.log("Messaging Agent has completed")

    def craft_message(
        self, description: str, deal_price: float, estimated_true_value: float
    ) -> str:
        user_prompt = "Please summarize this great deal in 2-3 sentences to be sent as an exciting push notification alerting the user about this deal.\n"
        user_prompt += f"Item Description: {description}\nOffered Price: {deal_price}\nEstimated true value: {estimated_true_value}"
        user_prompt += "\n\nRespond only with the 2-3 sentence message which will be used to alert & excite the user about this deal"
        response = completion(
            model=self.MODEL,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    def notify(self, description: str, deal_price: float, estimated_true_value: float, url: str, to_email: str = None):
        """
        Make an alert about the specified details
        
        Args:
            description: Item description
            deal_price: The deal price
            estimated_true_value: Estimated true value of the item
            url: URL to the deal
            to_email: Optional recipient email. Uses environment variable if not provided.
        """
        self.log("Messaging Agent is composing deal notification email")
        discount = estimated_true_value - deal_price
        
        # Format email with proper line breaks for readability
        text = "🎉 Deal Alert!\n\n"
        text += f"💰 Price: ${deal_price:.2f}\n"
        text += f"📊 Estimated Value: ${estimated_true_value:.2f}\n"
        text += f"🏷️ Discount: ${discount:.2f}\n\n"
        text += f"📦 Product: {description}\n\n"
        text += f"🔗 Link: {url}\n"
        
        self.send_email(text, to_email=to_email)
        self.log("Messaging Agent has completed")
