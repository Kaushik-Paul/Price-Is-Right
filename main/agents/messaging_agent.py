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

    def send_email(self, text: str, subject: str = "Deal Alert!"):
        """
        Send an email notification using the Mailjet API
        """
        self.log("Messaging Agent is sending an email notification")
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": self.from_email,
                        "Name": "Deal Finder Agent"
                    },
                    "To": [
                        {
                            "Email": self.to_email,
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

    def alert(self, opportunity: Opportunity):
        """
        Make an alert about the specified Opportunity
        """
        text = f"Deal Alert! Price=${opportunity.deal.price:.2f}, "
        text += f"Estimate=${opportunity.estimate:.2f}, "
        text += f"Discount=${opportunity.discount:.2f} :"
        text += opportunity.deal.product_description[:10] + "... "
        text += opportunity.deal.url
        self.send_email(text)
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

    def notify(self, description: str, deal_price: float, estimated_true_value: float, url: str):
        """
        Make an alert about the specified details
        """
        self.log("Messaging Agent is using LLM to craft the message")
        text = self.craft_message(description, deal_price, estimated_true_value)
        self.send_email(text[:200] + "... " + url)
        self.log("Messaging Agent has completed")
