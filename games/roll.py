from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
from database.mongo import get_user, update_user


def init_roll(bot: Client):

    # -------------------------------------------------
    # /roll — works in groups + DM
    # -------------------------------------------------
    @bot.on_message(filters.command(["roll", "dice"]))
    async def roll_cmd(_, msg: Message):

        user = msg.from_user
        if not user:
            return

        anim = await msg.reply("🎲 Rolling dice...")

        # Telegram dice animation
        dice = await bot.send_dice(msg.chat.id)
        await asyncio.sleep(3)

        value = dice.dice.value
        reward = value * 10

        data = get_user(user.id)
        new_bronze = data.get("bronze", 0) + reward

        update_user(user.id, {"bronze": new_bronze})

        await anim.edit(
            f"🎲 **You rolled:** `{value}`\n"
            f"🥉 **Reward:** `{reward} Bronze`"
        )

    # -------------------------------------------------
    # Auto-detected dice message in chat
    # -------------------------------------------------
    @bot.on_message(filters.dice)
    async def roll_handler(_, msg: Message):

        user = msg.from_user
        if not user:
            return

        value = msg.dice.value
        reward = value * 10

        data = get_user(user.id)
        new_bronze = data.get("bronze", 0) + reward

        update_user(user.id, {"bronze": new_bronze})

        await msg.reply(
            f"🎲 You rolled: `{value}`\n"
            f"🥉 Reward: `{reward} Bronze`"
        )
