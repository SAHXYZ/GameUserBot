# File: config.py

import os
from dotenv import load_dotenv

# Load .env automatically (important for VPS)
load_dotenv()

# Required credentials
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")

# String session for userbot
STRING_SESSION = os.getenv("STRING_SESSION")

# Database
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "GameUserBot")

# Safety checks
if not API_ID or not API_HASH or not STRING_SESSION:
    raise Exception("❌ Missing API_ID / API_HASH / STRING_SESSION in environment variables.")
