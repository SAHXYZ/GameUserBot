# File: GameBot/games/spin.py

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import random
import asyncio
from database.mongo import get_user, update_user
from utils.cooldown import check_cooldown, update_cooldown

# prevent double imports
if "module_loaded" in globals():
    raise SystemExit
module_loaded = True



def init_spin(bot: Client):

    @bot.on_message(filters.command("spin"))
    async def spin_cmd(_, msg: Message):
        user = msg.from_user
        if not user:
            return

        data = get_user(user.id)
        ok, wait, pretty = check_cooldown(data, "spin", 60)
        if not ok:
            return await msg.reply(
                f"⏳ Cooldown Active!\n\n"
                f"⏳ Wait **{pretty}** before spinning again."
            )

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔴 Red", callback_data="spin_red"),
                    InlineKeyboardButton("⚫ Black", callback_data="spin_black"),
                ],
                [
                    InlineKeyboardButton("🟢 Green", callback_data="spin_green"),
                    InlineKeyboardButton("🔵 Blue", callback_data="spin_blue"),
                ]
            ]
        )

        sent = await msg.reply("🎰 **Choose a colour:**", reply_markup=buttons)

        # Timeout system
        async def timeout_check():
            await asyncio.sleep(10)
            try:
                await sent.edit("⏳ **Spinning timed out. Use /spin again.**")
            except:
                pass

        sent.timeout_task = asyncio.create_task(timeout_check())

    @bot.on_callback_query(filters.regex(r"^spin_"))
    async def spin_result(_, cq: CallbackQuery):
        user = cq.from_user
        if not user:
            return

        choice = cq.data.replace("spin_", "")
        data = get_user(user.id)

        ok, wait, pretty = check_cooldown(data, "spin", 60)
        if not ok:
            return await cq.answer(
                f"⏳ Cooldown Active!\n\n"
                f"⏳ Wait **{pretty}** before spinning again.",
                show_alert=True
            )

        # Cancel timeout task when user clicks
        if hasattr(cq.message, "timeout_task"):
            try:
                cq.message.timeout_task.cancel()
            except:
                pass

        # Disable buttons
        try:
            await cq.message.edit_reply_markup(
                InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Spinning...", callback_data="none")]])
            )
        except:
            pass

        await cq.answer()

        # Slot animation
        dice = await bot.send_dice(cq.message.chat.id, emoji="🎰")
        await asyncio.sleep(3)

        value = dice.dice.value
        if value <= 30:
            actual = "red"
        elif value <= 58:
            actual = "black"
        elif value <= 62:
            actual = "green"
        else:
            actual = "blue"

        bronze = data.get("bronze", 0)
        streak = data.get("spin_streak", 0)

        # Reward ranges
        if actual in ["red", "black"]:
            win_min, win_max = 30, 120
            lose_min, lose_max = 15, 60
        elif actual == "green":
            win_min, win_max = 200, 400
            lose_min, lose_max = 80, 180
        else:
            win_min, win_max = 450, 1000
            lose_min, lose_max = 150, 300

        # Win / Loss logic
        if choice == actual:
            reward = random.randint(win_min, win_max)
            streak += 1

            if streak == 2:
                reward = int(reward * 1.10)
            elif streak == 3:
                reward = int(reward * 1.25)
            elif streak == 4:
                reward = int(reward * 1.40)
            elif streak >= 5:
                reward = int(reward * 1.60)

            bronze += reward
            result_text = (
                f"🎉 **You Won!**\n"
                f"🎯 Result: **{actual.upper()}**\n"
                f"🔥 Streak: **{streak} in a row!**\n"
                f"💰 Reward: **+{reward} Bronze**"
            )
        else:
            loss = random.randint(lose_min, lose_max)
            bronze = max(0, bronze - loss)
            streak = 0
            result_text = (
                f"😢 **You Lost!**\n"
                f"🎯 Result: **{actual.upper()}**\n"
                f"💔 Streak Reset\n"
                f"💰 Lost: **-{loss} Bronze**"
            )

        # ⛳ UPDATE COOLDOWN CORRECTLY
        new_data = update_cooldown(data, "spin")
        new_data["bronze"] = bronze
        new_data["spin_streak"] = streak
        update_user(user.id, new_data)

        await cq.message.reply(result_text)
