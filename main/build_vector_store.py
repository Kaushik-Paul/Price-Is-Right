import os
import chromadb
from datasets import load_dataset
from tqdm import tqdm

# Configuration
DATASET_ID = "kaushikpaul/items_prompts_lite"
DB_PATH = os.path.join(os.path.dirname(__file__), "products_vectorstore")
COLLECTION_NAME = "products"

def build():
    print(f"🚀 Loading dataset: {DATASET_ID}...")
    # Load from Hugging Face
    dataset = load_dataset(DATASET_ID, split="train")
    
    # Initialize ChromaDB
    print(f"📦 Initializing ChromaDB at {DB_PATH}...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # Delete collection if it exists to start fresh
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️ Deleted existing collection '{COLLECTION_NAME}'")
    except:
        pass
        
    collection = client.create_collection(name=COLLECTION_NAME)
    
    print(f"✨ Processing {len(dataset)} items...")
    
    # Prepare data for upload
    documents = []
    metadatas = []
    ids = []
    
    for i, item in enumerate(tqdm(dataset)):
        # Extract fields
        # The dataset format is: product_description, category, price
        desc = item.get("product_description", "")
        cat = item.get("category", "Unknown")
        
        if not desc:
            continue
            
        documents.append(desc)
        metadatas.append({"category": cat})
        ids.append(f"prod_{i}")
        
    # Batch add to Chroma (Chroma handles embeddings automatically via DefaultEmbeddingFunction)
    # Default is sentence-transformers/all-MiniLM-L6-v2 which is great for product matching
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end = min(i + batch_size, len(documents))
        collection.add(
            documents=documents[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end]
        )
        
    print(f"✅ Successfully populated vector store with {len(documents)} items!")
    print(f"📁 Location: {DB_PATH}")

if __name__ == "__main__":
    build()
