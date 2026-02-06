from agents.agent import Agent
from agents.deep_neural_network import DeepNeuralNetworkInference


class NeuralNetworkAgent(Agent):
    name = "Neural Network Agent"
    color = Agent.MAGENTA

    def __init__(self):
        """
        Initialize this object by setting up the neural network with random weights
        and the SentenceTransformer vector encoding model
        """
        self.log("Neural Network Agent is initializing")
        self.neural_network = DeepNeuralNetworkInference()
        self.neural_network.setup()
        self.log("Neural Network Agent is ready with random weights")

    def price(self, description: str) -> float:
        """
        Use the Deep Neural Network to estimate the price of the described item
        :param description: the product to be estimated
        :return: the price as a float
        """
        self.log("Neural Network Agent is starting a prediction")
        result = self.neural_network.inference(description)
        self.log(f"Neural Network Agent completed - predicting ${result:.2f}")
        return result
