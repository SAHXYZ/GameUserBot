# File: GameBot/games/daily.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import random
import time

from database.mongo import get_user, update_user

DAILY_COOLDOWN = 24 * 60 * 60
DAILY_MIN = 120
DAILY_MAX = 350


async def daily_reward(uid: int, msg: Message):
    user = get_user(uid)
    if not user:
        return await msg.reply("⚠️ No profile found. Use /start first.")

    now = int(time.time())
    last = user.get("last_daily")

    if last and now < last + DAILY_COOLDOWN:
        remaining = (last + DAILY_COOLDOWN) - now
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        return await msg.reply(f"⏳ Already claimed! Come back in **{h}h {m}m {s}s**.")

    reward = random.randint(DAILY_MIN, DAILY_MAX)

    update_user(uid, {
        "bronze": user.get("bronze", 0) + reward,
        "last_daily": now,
    })

    await msg.reply(
        f"🎁 **Daily Reward Claimed!**\n"
        f"💰 You received **{reward} bronze coins.**"
    )


def init_daily(bot: Client):

    @bot.on_message(filters.command("daily"))
    async def daily_cmd(_, msg: Message):

        # Detect private/group
        chat_type = str(msg.chat.type).lower()
        PRIVATE = ("private" in chat_type)

        # If used in group → redirect to DM same way as HELP
        if not PRIVATE:
            me = await bot.get_me()
            deep_link = f"https://t.me/{me.username}?start=daily"
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎁 Claim Daily Reward", url=deep_link)]]
            )
            return await msg.reply(
                "⚠️ Daily rewards can only be claimed in personal chat.\n"
                "Click below to continue 👇",
                reply_markup=kb
            )

        # DM → give reward
        await daily_reward(msg.from_user.id, msg)

    print("[loaded] games.daily")
