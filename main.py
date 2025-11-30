# File: GameBot/main.py
from pyrogram import Client
import importlib
import traceback
from config import API_ID, API_HASH, BOT_TOKEN
from database.mongo import client  # ensure MongoDB loads first

bot = Client(
    "GameBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1
)


def safe_init(module_name: str):
    try:
        mod = importlib.import_module(f"games.{module_name}")
        init_fn = getattr(mod, f"init_{module_name}", None)

        if callable(init_fn):
            init_fn(bot)
            print(f"[loaded] games.{module_name}")
        else:
            print(f"[skipped] games.{module_name}")

    except Exception as e:
        print(f"[ERROR] {module_name}: {e}")
        traceback.print_exc()


# Load modules
required_modules = [
    "start",
    "flip",
    "roll",
    "rob",
    "fight",
    "top",
    "help",
    "mine",
    "profile",
    "bet",
    "pay",
    "work",
    "shop",
    "sell",
    "spin",
    "equip",
    "daily",
    "convert",
    "wordchain",
    "xoxo",
    "guess",
    "callbacks"
]

optional_modules = []


if __name__ == "__main__":
    print("Initializing GameBot...")

    for module in required_modules:
        safe_init(module)

    for module in optional_modules:
        safe_init(module)

    print("✔ GameBot is running with MongoDB!")
    bot.run()   # ⬅️ block here and DO NOT add extra while-loops
