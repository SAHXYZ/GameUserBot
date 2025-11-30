from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.mongo import users
from utils.coins import total_bronze_value


# -----------------------------
# Keyboards
# -----------------------------
def leaderboard_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏆 Top Wealth", callback_data="top_coins"),
                InlineKeyboardButton("💬 Top Messages", callback_data="top_msgs")
            ]
        ]
    )


def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="lb_back")]])


# -----------------------------
# INIT
# -----------------------------
def init_top(bot: Client):

    @bot.on_message(filters.command("leaderboard"))
    async def show_menu(_, msg: Message):
        await msg.reply("📊 **Choose a leaderboard:**", reply_markup=leaderboard_menu())

    # -----------------------------
    # TOP BY WEALTH
    # -----------------------------
    @bot.on_callback_query(filters.regex("^top_coins$"))
    async def top_coins(client, cq: CallbackQuery):

        await cq.answer()

        # Fetch all users safely
        all_users = list(users.find({}))

        ranked = []
        for u in all_users:
            try:
                total = total_bronze_value(u)
                ranked.append((u["_id"], total, u))
            except:
                continue

        ranked = sorted(ranked, key=lambda x: x[1], reverse=True)[:10]

        if not ranked:
            return await cq.message.edit(
                "❗ No users found in leaderboard.",
                reply_markup=back_button()
            )

        text = "🏆 **Top Wealth Leaderboard**\n\n"
        rank = 1

        for uid, total, data in ranked:
            try:
                tg_user = await client.get_users(int(uid))
                name = tg_user.first_name
            except:
                name = f"User {uid}"

            text += (
                f"**{rank}. {name}**\n"
                f"🎖 {data.get('black_gold', 0)} "
                f"| 🏅 {data.get('platinum', 0)} "
                f"| 🥇 {data.get('gold', 0)} "
                f"| 🥈 {data.get('silver', 0)} "
                f"| 🥉 {data.get('bronze', 0)}\n"
                f"💰 **Total Value:** `{total}`\n\n"
            )
            rank += 1

        await cq.message.edit(text, reply_markup=back_button())

    # -----------------------------
    # TOP BY MESSAGES
    # -----------------------------
    @bot.on_callback_query(filters.regex("^top_msgs$"))
    async def top_msgs(client, cq: CallbackQuery):

        await cq.answer()

        pipeline = [
            {"$project": {"messages": 1}},
            {"$sort": {"messages": -1}},
            {"$limit": 10},
        ]

        top_list = list(users.aggregate(pipeline))

        if not top_list:
            return await cq.message.edit(
                "❗ No message data available.",
                reply_markup=back_button()
            )

        text = "💬 **Top Message Senders**\n\n"
        rank = 1

        for entry in top_list:
            uid = entry["_id"]
            msgs = entry.get("messages", 0)
            try:
                tg_user = await client.get_users(int(uid))
                name = tg_user.first_name
            except:
                name = f"User {uid}"

            text += f"**{rank}. {name}** — `{msgs}` messages\n"
            rank += 1

        await cq.message.edit(text, reply_markup=back_button())

    # -----------------------------
    # BACK BUTTON
    # -----------------------------
    @bot.on_callback_query(filters.regex("^lb_back$"))
    async def leaderboard_back(_, cq: CallbackQuery):
        await cq.answer()
        await cq.message.edit(
            "📊 **Choose a leaderboard:**",
            reply_markup=leaderboard_menu()
        )
