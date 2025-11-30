# File: GameBot/GameBot/games/flip.py

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import random
import asyncio
from database.mongo import get_user, update_user
from utils.cooldown import check_cooldown, update_cooldown


def init_flip(bot: Client):

    @bot.on_message(filters.command("flip"))
    async def flip_cmd(_, msg: Message):
        user = msg.from_user
        if not user:
            return

        data = get_user(user.id)
        ok, wait, pretty = check_cooldown(data, "flip", 30)
        if not ok:
            return await msg.reply(f"⏳ Wait **{pretty}** before flipping again.")

        buttons = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🙂 Heads", callback_data="flip_heads"),
                InlineKeyboardButton("⚡ Tails", callback_data="flip_tails")
            ]]
        )

        await msg.reply("🪙 **Choose Heads or Tails:**", reply_markup=buttons)

    @bot.on_callback_query(filters.regex(r"^flip_"))
    async def flip_result(_, cq: CallbackQuery):
        user = cq.from_user
        if not user:
            return

        choice = cq.data.replace("flip_", "")
        data = get_user(user.id)

        ok, wait, pretty = check_cooldown(data, "flip", 30)
        if not ok:
            return await cq.answer(f"⏳ Wait {pretty}!", show_alert=True)

        await cq.answer()

        # Disable buttons
        try:
            await cq.message.edit_reply_markup(None)
        except:
            pass

        # Edit message to flipping text
        try:
            await cq.message.edit_text("🪙 Flipping the coin...")
        except:
            pass

        # 💥 Send animation emoji separately
        coin_anim = await cq.message.reply("🪙")

        # wait for animation
        await asyncio.sleep(3)

        # Calculate result
        actual = random.choice(["heads", "tails"])
        bronze = data.get("bronze", 0)

        if choice == actual:
            reward = random.randint(10, 80)
            bronze += reward
            result_text = (
                f"🎉 **You Won!**\n"
                f"🪙 Coin: **{actual.upper()}**\n"
                f"🥉 Reward: **+{reward} Bronze**"
            )
        else:
            loss = random.randint(5, 35)
            bronze = max(0, bronze - loss)
            result_text = (
                f"😢 **You Lost!**\n"
                f"🪙 Coin: **{actual.upper()}**\n"
                f"🥉 Lost: **-{loss} Bronze**"
            )

        new_cd = update_cooldown(data, "flip")
        update_user(user.id, {"bronze": bronze, "cooldowns": new_cd})

        # Delete animation message (optional)
        try:
            await coin_anim.delete()
        except:
            pass

        # show final result on the ORIGINAL message
        await cq.message.edit_text(result_text)
