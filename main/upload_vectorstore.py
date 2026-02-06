import os
from huggingface_hub import HfApi

# Configuration
REPO_ID = "kaushikpaul/Price-Is-Right"
REPO_TYPE = "space"
# Path to this script's directory (main/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Local folder to upload (main/products_vectorstore)
LOCAL_FOLDER = os.path.join(BASE_DIR, "products_vectorstore")
# Target path in the repository (on Hugging Face Space)
PATH_IN_REPO = "main/products_vectorstore"

def upload():
    api = HfApi()
    
    if not os.path.exists(LOCAL_FOLDER):
        print(f"Error: Folder not found at {LOCAL_FOLDER}")
        return

    print(f"Uploading {LOCAL_FOLDER} to {REPO_ID} (Space)...")
    
    try:
        api.upload_folder(
            folder_path=LOCAL_FOLDER,
            path_in_repo=PATH_IN_REPO,
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            ignore_patterns=[], # This is crucial to bypass .gitignore
        )
        print("✅ Upload successful!")
        print(f"View files at: https://huggingface.co/spaces/{REPO_ID}/tree/main/{PATH_IN_REPO}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    upload()
