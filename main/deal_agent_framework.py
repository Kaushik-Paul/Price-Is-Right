import base64
import os
import sys
import logging
import json
from typing import List
from dotenv import load_dotenv
import chromadb
from google.cloud import storage
from agents.planning_agent import PlanningAgent
from agents.deals import Opportunity
from sklearn.manifold import TSNE
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv(override=True)

# Colors for logging
BG_BLUE = "\033[44m"
WHITE = "\033[37m"
RESET = "\033[0m"

# Colors for plot
CATEGORIES = [
    "Appliances",
    "Automotive",
    "Cell_Phones_and_Accessories",
    "Electronics",
    "Musical_Instruments",
    "Office_Products",
    "Tools_and_Home_Improvement",
    "Toys_and_Games",
]
COLORS = ["red", "blue", "brown", "orange", "yellow", "green", "purple", "cyan"]


def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [Agents] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


class DealAgentFramework:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB = os.path.join(BASE_DIR, "products_vectorstore")
    MEMORY_FILENAME = os.path.join(BASE_DIR, "database", "memory.json")
    
    # GCP Configuration
    USE_GCP = os.getenv("USE_GCP", "False").lower() == "true"
    GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME", "price-is-right-memory")
    GCP_BLOB_NAME = "memory.json"

    def __init__(self):
        init_logging()
        client = chromadb.PersistentClient(path=self.DB)
        
        # Initialize storage client if using GCP
        self.storage_client = None
        if self.USE_GCP:
            self.storage_client = self._init_gcp_client()
            
        self.memory = self.read_memory()
        self.collection = client.get_or_create_collection("products")
        self.planner = None
        self.user_email = None  # Email for sending deal alerts

    def _init_gcp_client(self):
        """Initializes GCP storage client from base64 secret."""
        try:
            base64_secret = os.getenv("GCP_SERVICE_ACCOUNT_BASE64")
            if not base64_secret:
                raise ValueError("GCP_SERVICE_ACCOUNT_BASE64 not found in environment")
            
            json_key = base64.b64decode(base64_secret).decode("utf-8")
            service_account_info = json.loads(json_key)
            return storage.Client.from_service_account_info(service_account_info)
        except Exception as e:
            logging.error(f"Failed to initialize GCP client: {e}")
            return None

    def _get_gcs_blob(self):
        """Returns the GCS blob for the memory file."""
        if not self.storage_client:
            return None
        bucket = self.storage_client.bucket(self.GCP_BUCKET_NAME)
        return bucket.blob(self.GCP_BLOB_NAME)

    def init_agents_as_needed(self):
        if not self.planner:
            self.log("Initializing Agent Framework")
            self.planner = PlanningAgent(self.collection)
            self.log("Agent Framework is ready")

    def read_memory(self) -> List[Opportunity]:
        if self.USE_GCP:
            blob = self._get_gcs_blob()
            if blob and blob.exists():
                try:
                    content = blob.download_as_text()
                    data = json.loads(content)
                    return [Opportunity(**item) for item in data]
                except Exception as e:
                    logging.error(f"Failed to read memory from GCP: {e}")
            return []
        else:
            if os.path.exists(self.MEMORY_FILENAME):
                with open(self.MEMORY_FILENAME, "r") as file:
                    data = json.load(file)
                opportunities = [Opportunity(**item) for item in data]
                return opportunities
            return []

    def write_memory(self) -> None:
        data = [opportunity.model_dump() for opportunity in self.memory]
        if self.USE_GCP:
            blob = self._get_gcs_blob()
            if blob:
                try:
                    blob.upload_from_string(
                        json.dumps(data, indent=2),
                        content_type="application/json"
                    )
                except Exception as e:
                    logging.error(f"Failed to write memory to GCP: {e}")
        else:
            with open(self.MEMORY_FILENAME, "w") as file:
                json.dump(data, file, indent=2)

    def reset_memory(self) -> None:
        """Truncates memory to the first 2 items."""
        truncated_data = [opportunity.model_dump() for opportunity in self.memory[:2]]
        self.memory = [Opportunity(**item) for item in truncated_data]
        self.write_memory()

    def log(self, message: str):
        text = BG_BLUE + WHITE + "[Agent Framework] " + message + RESET
        logging.info(text)

    def run(self) -> List[Opportunity]:
        self.init_agents_as_needed()
        logging.info("Kicking off Planning Agent")
        result = self.planner.plan(memory=self.memory, user_email=self.user_email)
        logging.info(f"Planning Agent has completed and returned: {result}")
        if result:
            # Add timestamp when the deal was added
            result.added_at = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
            self.memory.append(result)
            self.write_memory()
        return self.memory

    @classmethod
    def get_plot_data(cls, max_datapoints=2000):
        print(f"DEBUG: get_plot_data looking for DB at {cls.DB}")
        client = chromadb.PersistentClient(path=cls.DB)
        collection = client.get_or_create_collection("products")
        result = collection.get(
            include=["embeddings", "documents", "metadatas"], limit=max_datapoints
        )
        if result["embeddings"] is None or len(result["embeddings"]) == 0:
            return [], [], []
            
        vectors = np.array(result["embeddings"])
        documents = result["documents"]
        categories = [metadata["category"] for metadata in result["metadatas"]]
        colors = [COLORS[CATEGORIES.index(c)] for c in categories]
        
        # TSNE requires at least 4 samples for 3 components by default if no perplexity is set, 
        # or perplexity < n_samples. 
        if len(vectors) < 2:
            # Not enough data for TSNE
            return documents, np.zeros((len(vectors), 3)), colors
            
        tsne = TSNE(n_components=3, random_state=42, n_jobs=-1, perplexity=min(30, len(vectors) - 1))
        reduced_vectors = tsne.fit_transform(vectors)
        return documents, reduced_vectors, colors


if __name__ == "__main__":
    DealAgentFramework().run()
