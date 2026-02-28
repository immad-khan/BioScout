from dotenv import load_dotenv
import os

load_dotenv()
uri = os.environ.get("MONGO_URI")
print(f"Loaded URI from .env: {uri}")
