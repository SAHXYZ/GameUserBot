# File: GameBot/games/equip.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import traceback
from database.mongo import get_user, update_user

TOOLS = ["Wooden", "Stone", "Iron", "Platinum", "Diamond", "Emerald"]

def init_equip(bot: Client):

    @bot.on_message(filters.command("equip"))
    async def equip_cmd(_, msg: Message):
        try:
            user = get_user(msg.from_user.id)
            if not user:
                return await msg.reply("❌ Use /start first.")

            inv = user.setdefault("inventory", {})
            owned = inv.get("tools", [])

            if not owned:
                return await msg.reply("❌ You don't own any tools.")

            # buttons for each tool
            buttons = [
                [InlineKeyboardButton(tool, callback_data=f"equip_tool:{tool}")]
                for tool in owned
                if tool in TOOLS
            ]

            await msg.reply(
                "🔧 **Choose a tool to equip:**",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception:
            traceback.print_exc()
            await msg.reply("⚠️ Error.")

    @bot.on_callback_query(filters.regex(r"^equip_tool:"))
    async def cb_equip_tool(_, cq: CallbackQuery):
        try:
            tool = cq.data.split(":")[1]

            user = get_user(cq.from_user.id)
            if not user:
                return await cq.answer("❌ Profile not found.")

            inv = user.setdefault("inventory", {})
            owned = inv.get("tools", [])

            if tool not in owned:
                return await cq.answer("❌ You don't own this tool.")

            # Equip tool
            user["equipped"] = tool
            update_user(cq.from_user.id, user)

            await cq.message.edit_text(f"✅ Equipped **{tool}** successfully!")
            await cq.answer()

        except Exception:
            traceback.print_exc()
            await cq.answer("⚠️ Error equipping tool.")

    print("[loaded] games.equip")
