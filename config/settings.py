import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY") # Will be None if not set in .env
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")