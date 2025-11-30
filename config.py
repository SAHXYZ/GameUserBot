import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# string session for USERBOT
STRING_SESSION = os.getenv("STRING_SESSION")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "GameUserBot")
