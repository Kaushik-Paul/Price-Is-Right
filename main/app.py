from dotenv import load_dotenv
from deal_agent_framework import DealAgentFramework
from ui import GradioUI

load_dotenv(override=True)


class App:
    """Main application entry point."""
    
    def __init__(self):
        self.agent_framework = None

    def get_agent_framework(self):
        """Lazy initialization of the agent framework."""
        if not self.agent_framework:
            self.agent_framework = DealAgentFramework()
        return self.agent_framework

    def run(self):
        """Start the application with Gradio UI."""
        ui = GradioUI(self.get_agent_framework())
        ui.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    App().run()
