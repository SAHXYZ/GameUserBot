# File: GameBot/games/mine.py
from pyrogram import Client, filters
from pyrogram.types import Message
import random
import time
import traceback
from database.mongo import get_user, update_user


# ==========================================================
# 🔨 Allowed Tools (only these 6)
# ==========================================================
TOOLS = {
    "Wooden":   {"power": 1, "durability": 50, "price": 50},
    "Stone":    {"power": 2, "durability": 100, "price": 150},
    "Iron":     {"power": 3, "durability": 150, "price": 400},
    "Platinum": {"power": 5, "durability": 275, "price": 3000},
    "Diamond":  {"power": 7, "durability": 350, "price": 8000},
    "Emerald":  {"power": 9, "durability": 450, "price": 20000},
}

# ==========================================================
# 💎 Ore Table
# ==========================================================
ORES = [
    {"name": "Coal", "value": 2, "rarity": 60},
    {"name": "Copper", "value": 5, "rarity": 45},
    {"name": "Iron", "value": 12, "rarity": 30},
    {"name": "Gold", "value": 25, "rarity": 15},
    {"name": "Diamond", "value": 100, "rarity": 5},
]

# Weighted ore choosing
def choose_ore():
    pool = []
    for ore in ORES:
        pool.extend([ore["name"]] * max(1, ore["rarity"]))
    return random.choice(pool)


# ==========================================================
# ⛏ INIT MINE MODULE
# ==========================================================
def init_mine(bot: Client):

    # ⛏️ /mine command
    @bot.on_message(filters.command("mine"))
    async def mine_cmd(_, msg: Message):
        try:
            user = get_user(msg.from_user.id)
            if not user:
                await msg.reply("❌ Please use /start first to create your profile.")
                return

            # Ensure inventory & ores exist
            user.setdefault("inventory", {})
            user["inventory"].setdefault("ores", {})

            # Cooldown
            now = int(time.time())
            last = user.get("last_mine", 0)
            cooldown = 5

            if now < last + cooldown:
                wait = (last + cooldown) - now
                await msg.reply(f"⏳ You're mining too fast! Wait **{wait}s**.")
                return

            # Update last mine time
            user["last_mine"] = now

            # Pick ore
            ore = choose_ore()
            amount = random.randint(1, 3)

            user["inventory"]["ores"].setdefault(ore, 0)
            user["inventory"]["ores"][ore] += amount

            update_user(msg.from_user.id, user)

            await msg.reply(f"⛏️ You mined **{amount}× {ore}**!")

        except Exception:
            traceback.print_exc()
            try:
                await msg.reply("⚠️ An error occurred during mining.")
            except:
                pass

    print("[loaded] games.mine")
