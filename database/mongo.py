# File: database/mongo.py
from pymongo import MongoClient, errors
import os
import sys


# -------------------------------------------------
# ENVIRONMENT VARIABLES & VALIDATION
# -------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "GameBot")

if not MONGO_URI:
    print("❌ MONGO_URI is missing in environment variables.")
    sys.exit(1)


# -------------------------------------------------
# CONNECT TO MONGO (SAFE CONNECTION CHECK)
# -------------------------------------------------
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000  # prevents long hang on bad URI
    )
    client.admin.command("ping")  # force connection check immediately
    print("✅ MongoDB connected successfully.")
except errors.ServerSelectionTimeoutError:
    print("❌ Failed to connect to MongoDB — invalid URI or network blocked.")
    sys.exit(1)
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    sys.exit(1)


db = client[DB_NAME]
users = db["users"]


# -------------------------------------------------
# DEFAULT USER TEMPLATE (Single Source of Truth)
# -------------------------------------------------
DEFAULT_USER = {
    "black_gold": 0,
    "platinum": 0,
    "gold": 0,
    "silver": 0,
    "bronze": 0,

    "messages": 0,
    "fight_wins": 0,
    "rob_success": 0,
    "rob_fail": 0,

    "cooldowns": {},

    "inventory": {
        "ores": {},
        "items": []
    },

    "tools": {"Wooden": 1},
    "equipped": "Wooden",
    "tool_durabilities": {"Wooden": 50},
    "last_mine": 0,

    "badges": [],

    "daily_streak": 0,
    "last_daily": 0,
}


# -------------------------------------------------
# GET USER (Auto-Fix Old Structure)
# -------------------------------------------------
def get_user(user_id):
    user_id = str(user_id)
    user = users.find_one({"_id": user_id})

    # Create if not exists
    if not user:
        new_user = {"_id": user_id}
        new_user.update(DEFAULT_USER)
        users.insert_one(new_user)
        return new_user

    # Fix existing structure
    updated_fields = {}
    for key, default in DEFAULT_USER.items():
        if key not in user:
            updated_fields[key] = default
            continue

        # Patch old installs where last_daily was None
        if key == "last_daily" and (user[key] is None):
            updated_fields[key] = 0
            continue

        # Deep fix: inventory
        if key == "inventory":
            inv = user.get("inventory", {})
            if not isinstance(inv, dict):
                inv = {"ores": {}, "items": []}
            inv.setdefault("ores", {})
            inv.setdefault("items", [])
            updated_fields[key] = inv
            continue

        updated_fields[key] = user[key]

    # Save changes if any
    if updated_fields != user:
        users.update_one({"_id": user_id}, {"$set": updated_fields})

    return updated_fields


# -------------------------------------------------
# CREATE USER IF NOT EXISTS
# -------------------------------------------------
def create_user_if_not_exists(user_id, name):
    user_id = str(user_id)
    user = users.find_one({"_id": user_id})

    if user:
        return user

    new_user = {"_id": user_id, "name": name}
    new_user.update(DEFAULT_USER)
    users.insert_one(new_user)
    return new_user


# -------------------------------------------------
# UPDATE USER
# -------------------------------------------------
def update_user(user_id, data: dict):
    users.update_one(
        {"_id": str(user_id)},
        {"$set": data},
        upsert=True
    )
