# File: GameBot/games/sell.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import traceback
from database.mongo import get_user, update_user

if "module_loaded" in globals():
    raise SystemExit
module_loaded = True


# Ore values
ORE_VALUES = {
    "Coal": 2,
    "Copper": 5,
    "Iron": 12,
    "Gold": 25,
    "Diamond": 100,
}

def init_sell(bot: Client):

    # /sell (show available ores)
    @bot.on_message(filters.command("sell"))
    async def sell_cmd(_, msg: Message):
        user = get_user(msg.from_user.id)
        if not user:
            return await msg.reply("❌ Use /start first.")

        inv = user.setdefault("inventory", {})
        ores = inv.setdefault("ores", {})

        if not ores:
            return await msg.reply("❌ You don't have any ores to sell.")

        # Create buttons for each ore
        buttons = [
            [InlineKeyboardButton(f"Sell {ore} ({amount})", callback_data=f"sell_ore:{ore}")]
            for ore, amount in ores.items()
        ]

        await msg.reply(
            "🛒 **Select the ore you want to sell:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Callback — Sell selected ore
    @bot.on_callback_query(filters.regex(r"^sell_ore:"))
    async def sell_ore(_, cq: CallbackQuery):
        try:
            ore = cq.data.split(":")[1]

            user = get_user(cq.from_user.id)
            if not user:
                return await cq.answer("❌ Profile not found.")

            inv = user.setdefault("inventory", {})
            ores = inv.setdefault("ores", {})

            amount = ores.get(ore, 0)
            if amount <= 0:
                return await cq.answer("❌ No such ore left.")

            price = ORE_VALUES.get(ore, 1)
            earned = amount * price

            # Update wallet
            user["bronze"] = user.get("bronze", 0) + earned
            ores.pop(ore, None)

            update_user(cq.from_user.id, user)

            try:
                await cq.message.edit_text(
                    f"🛒 Sold **{amount}× {ore}** for **{earned} Bronze 🥉**!"
                )
            except:
                pass

            await cq.answer()

        except Exception:
            traceback.print_exc()
            try:
                await cq.answer("⚠️ Error selling ore.")
            except:
                pass

    print("[loaded] games.sell")
