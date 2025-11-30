from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import get_user, update_user
import re

# Conversion rates (upgrade side)
BRONZE_TO_SILVER = 100
SILVER_TO_GOLD = 100
GOLD_TO_PLATINUM = 100

# Downgrade rate: 1 higher tier -> 100 lower tier
DOWNGRADE_RATE = 100

# In-memory state for "enter amount" flow
pending_amount = {}


def init_convert(bot: Client):

    # ---------------------- Root keyboard builders ----------------------
    def root_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⭡ Upgrade", callback_data="conv_mode_up")],
            [InlineKeyboardButton("⭣ Downgrade", callback_data="conv_mode_down")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
        ])

    def upgrade_list_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🥉 Bronze → 🥈 Silver", callback_data="conv_up_bs")],
            [InlineKeyboardButton("🥈 Silver → 🥇 Gold", callback_data="conv_up_sg")],
            [InlineKeyboardButton("🥇 Gold → 🏅 Platinum", callback_data="conv_up_gp")],
            [InlineKeyboardButton("🔙 Back", callback_data="go_convert_menu")]
        ])

    def downgrade_list_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏅 Platinum → 🥇 Gold", callback_data="conv_down_pg")],
            [InlineKeyboardButton("🥇 Gold → 🥈 Silver", callback_data="conv_down_gs")],
            [InlineKeyboardButton("🥈 Silver → 🥉 Bronze", callback_data="conv_down_sb")],
            [InlineKeyboardButton("🔙 Back", callback_data="go_convert_menu")]
        ])

    # ---------------------- /convert ----------------------
    @bot.on_message(filters.command("convert"))
    async def convert_cmd(_, msg: Message):
        await msg.reply(
            "💰 **Convert Your Coins**\n\nChoose a mode:",
            reply_markup=root_keyboard()
        )

    # ---------------------- Main convert menu (callback) ----------------------
    @bot.on_callback_query(filters.regex("^go_convert_menu$"))
    async def go_convert_menu_cb(client, cq: CallbackQuery):
        pending_amount.pop(cq.from_user.id, None)
        await cq.message.edit_text(
            "💰 **Convert Your Coins**\n\nChoose a mode:",
            reply_markup=root_keyboard()
        )
        await cq.answer()

    # ---------------------- Mode selection: Upgrade / Downgrade ----------------------
    @bot.on_callback_query(filters.regex("^conv_mode_"))
    async def conv_mode_cb(client, cq: CallbackQuery):
        pending_amount.pop(cq.from_user.id, None)
        if cq.data == "conv_mode_up":
            await cq.message.edit_text(
                "💹 **Upgrade Coins**\n\nChoose which coins to upgrade:",
                reply_markup=upgrade_list_keyboard()
            )
        else:
            await cq.message.edit_text(
                "📉 **Downgrade Coins**\n\nChoose which coins to downgrade:",
                reply_markup=downgrade_list_keyboard()
            )
        await cq.answer()

    # ---------------------- Upgrade pair selection ----------------------
    @bot.on_callback_query(filters.regex("^conv_up_"))
    async def conv_up_pair_cb(client, cq: CallbackQuery):
        user_id = cq.from_user.id
        pending_amount.pop(user_id, None)
        data = get_user(user_id)

        if cq.data == "conv_up_bs":
            src, dst, rate, icon = "bronze", "silver", BRONZE_TO_SILVER, "🥉 → 🥈"
        elif cq.data == "conv_up_sg":
            src, dst, rate, icon = "silver", "gold", SILVER_TO_GOLD, "🥈 → 🥇"
        else:
            src, dst, rate, icon = "gold", "platinum", GOLD_TO_PLATINUM, "🥇 → 🏅"

        cur = data[src]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⌨️ Convert by Amount", callback_data=f"camt|up|{src}|{dst}|{rate}|{cq.data}")],
            [InlineKeyboardButton("⚡ Convert Max", callback_data=f"cmax|up|{src}|{dst}|{rate}|{cq.data}")],
            [InlineKeyboardButton("🔙 Back", callback_data="conv_mode_up")]
        ])

        await cq.message.edit_text(
            f"💰 **Upgrade Coins**\n\n{icon}\nConversion Rate: **{rate} {src} → 1 {dst}**\n\n"
            f"You currently have **{cur} {src}**.\n\nChoose how you want to convert:",
            reply_markup=keyboard
        )
        await cq.answer()

    # ---------------------- Downgrade pair selection ----------------------
    @bot.on_callback_query(filters.regex("^conv_down_"))
    async def conv_down_pair_cb(client, cq: CallbackQuery):
        user_id = cq.from_user.id
        pending_amount.pop(user_id, None)
        data = get_user(user_id)

        if cq.data == "conv_down_pg":
            src, dst, icon = "platinum", "gold", "🏅 → 🥇"
        elif cq.data == "conv_down_gs":
            src, dst, icon = "gold", "silver", "🥇 → 🥈"
        else:
            src, dst, icon = "silver", "bronze", "🥈 → 🥉"

        rate = DOWNGRADE_RATE
        cur = data[src]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⌨️ Convert by Amount", callback_data=f"camt|down|{src}|{dst}|{rate}|{cq.data}")],
            [InlineKeyboardButton("⚡ Convert Max", callback_data=f"cmax|down|{src}|{dst}|{rate}|{cq.data}")],
            [InlineKeyboardButton("🔙 Back", callback_data="conv_mode_down")]
        ])

        await cq.message.edit_text(
            f"💰 **Downgrade Coins**\n\n{icon}\nConversion Rate: **1 {src} → {rate} {dst}**\n\n"
            f"You currently have **{cur} {src}**.\n\nChoose how you want to convert:",
            reply_markup=keyboard
        )
        await cq.answer()

    # ---------------------- Convert Max ----------------------
    @bot.on_callback_query(filters.regex("^cmax"))
    async def convert_max_cb(client, cq: CallbackQuery):
        _, mode, src, dst, rate, ctype = cq.data.split("|")
        rate = int(rate)
        user_id = cq.from_user.id

        data = get_user(user_id)

        if mode == "up":
            src_balance = data[src]
            if src_balance < rate:
                return await cq.answer("Nothing to convert.", show_alert=True)
            gained = src_balance // rate
            data[src] -= gained * rate
            data[dst] += gained
        else:
            src_balance = data[src]
            if src_balance <= 0:
                return await cq.answer("Nothing to convert.", show_alert=True)
            gained = src_balance * rate
            data[src] = 0
            data[dst] += gained

        update_user(user_id, data)

        await cq.message.edit_text(
            "💰 **Converted successfully!**\n\nFull conversion completed.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Convert Again", callback_data=ctype)],
                [InlineKeyboardButton("🔙 Main Conversion Menu", callback_data="go_convert_menu")]
            ])
        )
        await cq.answer()

    # ---------------------- Convert by Amount Start ----------------------
    @bot.on_callback_query(filters.regex("^camt"))
    async def convert_amount_start(client, cq: CallbackQuery):
        _, mode, src, dst, rate, ctype = cq.data.split("|")
        user_id = cq.from_user.id
        rate = int(rate)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Main Conversion Menu", callback_data="go_convert_menu")]]
        )
        sent = await cq.message.edit_text(
            "⌨️ **Enter Amount**\n\nSend the number of coins you want to convert.\n"
            "You can send a plain number or a sentence with a number.\n",
            reply_markup=keyboard
        )

        pending_amount[user_id] = {
            "mode": mode,
            "src": src,
            "dst": dst,
            "rate": rate,
            "ctype": ctype,
            "chat_id": sent.chat.id,
            "message_id": sent.id,
            "keyboard": keyboard,
        }
        await cq.answer()

    # ---------------------- custom filter: user expecting amount input ----------------------
    def expecting_amount_filter(_, __, msg: Message) -> bool:
        return bool(msg.from_user and msg.from_user.id in pending_amount)

    expecting_amount = filters.create(expecting_amount_filter)

    # ---------------------- Convert by Amount Handler ----------------------
    # group=2 so it runs AFTER quiz answer handler (group=1)
    @bot.on_message(filters.text & ~filters.command("convert") & expecting_amount, group=2)
    async def handle_amount_input(client, msg: Message):
        user = msg.from_user
        state = pending_amount.get(user.id)
        if not state:
            return

        numbers = re.findall(r"\d+", msg.text)
        if not numbers:
            return await client.edit_message_text(
                state["chat_id"],
                state["message_id"],
                "❌ **Please enter a valid number.**",
                reply_markup=state["keyboard"],
            )

        amount = int(numbers[0])
        if amount <= 0:
            return await client.edit_message_text(
                state["chat_id"],
                state["message_id"],
                "❌ **Amount must be greater than zero.**",
                reply_markup=state["keyboard"],
            )

        data = get_user(user.id)
        src, dst, mode, rate = state["src"], state["dst"], state["mode"], state["rate"]

        if mode == "up":
            needed = amount * rate
            if data[src] < needed:
                return await client.edit_message_text(
                    state["chat_id"],
                    state["message_id"],
                    f"❌ Not enough {src}. Requires {needed}, but you have {data[src]}.",
                    reply_markup=state["keyboard"],
                )
            data[src] -= needed
            data[dst] += amount
        else:
            if data[src] < amount:
                return await client.edit_message_text(
                    state["chat_id"],
                    state["message_id"],
                    f"❌ Not enough {src}. You tried {amount}, but you have {data[src]}.",
                    reply_markup=state["keyboard"],
                )
            gained = amount * rate
            data[src] -= amount
            data[dst] += gained

        update_user(user.id, data)
        pending_amount.pop(user.id, None)

        await client.edit_message_text(
            state["chat_id"],
            state["message_id"],
            "💰 **Converted successfully!**\n\nTransaction complete.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Convert Again", callback_data=state["ctype"])],
                [InlineKeyboardButton("🔙 Main Conversion Menu", callback_data="go_convert_menu")]
            ]),
        )
