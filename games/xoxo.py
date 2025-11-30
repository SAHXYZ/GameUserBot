# File: games/xoxo.py

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from database.mongo import get_user, update_user

# ==========================================================
# In-memory state
# ==========================================================

# Active challenges (before game starts)
# key: (chat_id, message_id)
# value: {
#   "creator_id": int,
#   "creator_name": str,
#   "bet": int,
# }
xoxo_challenges = {}

# Active games (after bet accepted)
# key: (chat_id, message_id)
# value: {
#   "board": list[str],  # 9 cells: " ", "X", "O"
#   "current": "X" | "O",
#   "player_x_id": int,
#   "player_x_name": str,
#   "player_o_id": int,
#   "player_o_name": str,
#   "bet": int,
#   "pot": int,
#   "finished": bool,
# }
xoxo_games = {}

# Waiting for bet change input
# key: (chat_id, user_id) -> message_id of the challenge message
xoxo_bet_wait = {}


def _make_key(chat_id: int, message_id: int):
    return (int(chat_id), int(message_id))


def _symbol_to_emoji(symbol: str) -> str:
    if symbol == "X":
        return "❌"
    if symbol == "O":
        return "⭕"
    return "⬜"   # empty


def _build_board_markup(board, finished: bool = False) -> InlineKeyboardMarkup:
    """
    Build 3×3 inline keyboard.
    When finished=True, cells use 'xoxo_done' so game can't continue.
    """
    rows = []
    for r in range(3):
        buttons = []
        for c in range(3):
            idx = r * 3 + c
            text = _symbol_to_emoji(board[idx])
            if finished:
                data = "xoxo_done"
            else:
                data = f"xoxo_{idx}"
            buttons.append(InlineKeyboardButton(text, callback_data=data))
        rows.append(buttons)
    return InlineKeyboardMarkup(rows)


def _build_challenge_markup() -> InlineKeyboardMarkup:
    """
    Challenge control buttons.
    Usable by anyone before game starts.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept Bet", callback_data="xoxo_accept"),
                InlineKeyboardButton("❌ Decline", callback_data="xoxo_decline"),
            ],
            [
                InlineKeyboardButton("🔄 Change Bet", callback_data="xoxo_change"),
                InlineKeyboardButton("🛑 Cancel", callback_data="xoxo_cancel"),
            ],
        ]
    )


def _check_winner(board):
    """
    Returns:
        "X" | "O" | "draw" | None
    """
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
        (0, 4, 8), (2, 4, 6),             # diagonals
    ]

    for a, b, c in wins:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]

    if " " not in board:
        return "draw"

    return None


def init_xoxo(bot: Client):

    # ======================================================
    # /xoxo <bet> — create challenge
    # ======================================================
    @bot.on_message(filters.command("xoxo"))
    async def cmd_xoxo(_, msg: Message):
        if not msg.from_user or msg.from_user.is_bot:
            return

        chat_id = msg.chat.id

        # Parse bet amount
        if len(msg.command) < 2:
            return await msg.reply(
                "💰 Usage: <code>/xoxo &lt;bet_amount&gt;</code>\n"
                "Example: <code>/xoxo 50</code>",
                quote=True,
            )

        bet_str = msg.command[1]
        if not bet_str.isdigit():
            return await msg.reply("❌ Bet amount must be a positive number.", quote=True)

        bet = int(bet_str)
        if bet <= 0:
            return await msg.reply("❌ Bet amount must be greater than zero.", quote=True)

        # Check user's balance
        try:
            user = get_user(msg.from_user.id)
        except Exception:
            user = None

        if not user:
            return await msg.reply("⚠️ You don't have a profile yet. Use /start first.", quote=True)

        bronze = int(user.get("bronze", 0))
        if bronze < bet:
            return await msg.reply(
                f"❌ You don't have enough Bronze.\n"
                f"You have: <b>{bronze}</b> 🥉\n"
                f"Required: <b>{bet}</b> 🥉",
                quote=True,
            )

        # Create challenge
        text = (
            "❌⭕ <b>XO XO — Bet Challenge</b>\n\n"
            f"👤 <b>Challenger:</b> {msg.from_user.mention}\n"
            f"💰 <b>Bet:</b> <code>{bet}</code> Bronze 🥉 (each)\n\n"
            "Anyone can accept this challenge.\n"
            "Both players will be charged the bet amount when the game starts.\n\n"
            "➡ Choose an option below:"
        )

        sent = await msg.reply(
            text,
            reply_markup=_build_challenge_markup(),
            quote=True,
        )

        key = _make_key(sent.chat.id, sent.id)
        xoxo_challenges[key] = {
            "creator_id": msg.from_user.id,
            "creator_name": msg.from_user.first_name,
            "bet": bet,
        }

    # ======================================================
    # Challenge callback helpers
    # ======================================================
    async def _get_challenge(cq: CallbackQuery):
        if not cq.message:
            return None, None
        key = _make_key(cq.message.chat.id, cq.message.id)
        return key, xoxo_challenges.get(key)

    # ---------------------- Accept Bet ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_accept$"))
    async def cb_xoxo_accept(_, cq: CallbackQuery):
        key, challenge = await _get_challenge(cq)
        if not challenge:
            return await cq.answer("⚠️ This challenge is no longer active.", show_alert=True)

        if not cq.from_user or cq.from_user.is_bot:
            return await cq.answer()

        challenger_id = challenge["creator_id"]
        challenger_name = challenge["creator_name"]
        opponent_id = cq.from_user.id
        opponent_name = cq.from_user.first_name
        bet = challenge["bet"]

        # Cannot play against self
        if opponent_id == challenger_id:
            return await cq.answer("You can't accept your own challenge.", show_alert=True)

        # Check balances for both
        try:
            user_a = get_user(challenger_id)
            user_b = get_user(opponent_id)
        except Exception:
            user_a = user_b = None

        if not user_a or not user_b:
            return await cq.answer("⚠️ One of the players has no profile. Use /start.", show_alert=True)

        bronze_a = int(user_a.get("bronze", 0))
        bronze_b = int(user_b.get("bronze", 0))

        if bronze_a < bet or bronze_b < bet:
            msg_text = "❌ Bet cannot be started due to low balance:\n\n"
            if bronze_a < bet:
                msg_text += (
                    f"• {challenger_name}: <b>{bronze_a}</b> 🥉 (needs {bet})\n"
                )
            if bronze_b < bet:
                msg_text += (
                    f"• {opponent_name}: <b>{bronze_b}</b> 🥉 (needs {bet})\n"
                )
            msg_text += "\nChallenge cancelled."
            xoxo_challenges.pop(key, None)
            await cq.message.edit_text(msg_text)
            return await cq.answer("Insufficient balance.", show_alert=True)

        # Deduct bet from both (lock pot)
        try:
            update_user(challenger_id, {"bronze": bronze_a - bet})
            update_user(opponent_id, {"bronze": bronze_b - bet})
        except Exception:
            return await cq.answer("Database error, try again later.", show_alert=True)

        # Remove challenge, start game
        xoxo_challenges.pop(key, None)

        board = [" "] * 9
        pot = bet * 2

        xoxo_games[key] = {
            "board": board,
            "current": "X",
            "player_x_id": challenger_id,
            "player_x_name": challenger_name,
            "player_o_id": opponent_id,
            "player_o_name": opponent_name,
            "bet": bet,
            "pot": pot,
            "finished": False,
        }

        text = (
            "❌⭕ <b>XO XO — Match Started</b>\n\n"
            f"❌ <b>X:</b> {challenger_name}\n"
            f"⭕ <b>O:</b> {opponent_name}\n"
            f"💰 <b>Bet Locked:</b> <code>{bet}</code> 🥉 each (Pot: <code>{pot}</code> 🥉)\n\n"
            f"Turn: ❌ <b>{challenger_name}</b>\n"
            "Tap a square to play."
        )

        await cq.message.edit_text(
            text,
            reply_markup=_build_board_markup(board),
        )
        await cq.answer("Bet accepted, game started!")

    # ---------------------- Decline Bet ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_decline$"))
    async def cb_xoxo_decline(_, cq: CallbackQuery):
        key, challenge = await _get_challenge(cq)
        if not challenge:
            return await cq.answer("This challenge is no longer active.", show_alert=True)

        if not cq.from_user:
            return await cq.answer()

        decliner = cq.from_user.first_name
        bet = challenge["bet"]
        creator_name = challenge["creator_name"]

        text = (
            "❌⭕ <b>XO XO — Challenge Declined</b>\n\n"
            f"👤 <b>Challenger:</b> {creator_name}\n"
            f"💰 <b>Bet:</b> <code>{bet}</code> Bronze 🥉\n\n"
            f"🚫 <b>{decliner}</b> declined the challenge."
        )

        xoxo_challenges.pop(key, None)
        await cq.message.edit_text(text)
        await cq.answer("Challenge declined.")

    # ---------------------- Cancel Challenge (anyone) ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_cancel$"))
    async def cb_xoxo_cancel(_, cq: CallbackQuery):
        key, challenge = await _get_challenge(cq)
        if not challenge:
            return await cq.answer("This challenge is no longer active.", show_alert=True)

        bet = challenge["bet"]
        creator_name = challenge["creator_name"]
        who = cq.from_user.first_name if cq.from_user else "Someone"

        text = (
            "❌⭕ <b>XO XO — Challenge Cancelled</b>\n\n"
            f"👤 <b>Challenger:</b> {creator_name}\n"
            f"💰 <b>Bet:</b> <code>{bet}</code> Bronze 🥉\n\n"
            f"🛑 Cancelled by <b>{who}</b>."
        )

        xoxo_challenges.pop(key, None)
        await cq.message.edit_text(text)
        await cq.answer("Challenge cancelled.")

    # ---------------------- Change Bet (anyone triggers) ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_change$"))
    async def cb_xoxo_change(_, cq: CallbackQuery):
        key, challenge = await _get_challenge(cq)
        if not challenge:
            return await cq.answer("This challenge is no longer active.", show_alert=True)

        if not cq.from_user or cq.from_user.is_bot:
            return await cq.answer()

        chat_id = cq.message.chat.id
        user_id = cq.from_user.id

        # Mark that this user is about to send a new bet
        xoxo_bet_wait[(int(chat_id), int(user_id))] = cq.message.id

        await cq.answer()
        await cq.message.reply(
            f"🔄 <b>{cq.from_user.first_name}</b>, send the new bet amount (number only).",
            quote=True,
        )

    # ======================================================
    # Message filter for bet change input
    # ======================================================
    def bet_wait_filter(_, __, msg: Message) -> bool:
        if not msg.from_user:
            return False
        key = (int(msg.chat.id), int(msg.from_user.id))
        return key in xoxo_bet_wait

    bet_wait = filters.create(bet_wait_filter)

    # ---------------------- Handle new bet amount ----------------------
    @bot.on_message(filters.text & bet_wait)
    async def handle_bet_change(_, msg: Message):
        chat_id = int(msg.chat.id)
        user_id = int(msg.from_user.id)
        key_wait = (chat_id, user_id)

        msg_id = xoxo_bet_wait.pop(key_wait, None)
        if msg_id is None:
            return

        challenge_key = (chat_id, int(msg_id))
        challenge = xoxo_challenges.get(challenge_key)
        if not challenge:
            return await msg.reply("⚠️ That challenge is no longer active.", quote=True)

        bet_str = msg.text.strip()
        if not bet_str.isdigit():
            return await msg.reply("❌ Bet amount must be a positive number.", quote=True)

        new_bet = int(bet_str)
        if new_bet <= 0:
            return await msg.reply("❌ Bet amount must be greater than zero.", quote=True)

        # Just update the challenge bet
        challenge["bet"] = new_bet

        text = (
            "❌⭕ <b>XO XO — Bet Challenge</b>\n\n"
            f"👤 <b>Challenger:</b> {challenge['creator_name']}\n"
            f"💰 <b>Bet:</b> <code>{new_bet}</code> Bronze 🥉 (each)\n\n"
            "Anyone can accept this challenge.\n"
            "Both players will be charged the bet amount when the game starts.\n\n"
            "➡ Choose an option below:"
        )

        # Edit the original challenge message with new bet
        try:
            await msg._client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=_build_challenge_markup(),
            )
        except Exception:
            pass

        await msg.reply(
            f"✅ Bet updated to <b>{new_bet}</b> Bronze 🥉.",
            quote=True,
        )

    # ======================================================
    # XO XO board callbacks
    # ======================================================
    async def _get_game(cq: CallbackQuery):
        if not cq.message:
            return None, None
        key = _make_key(cq.message.chat.id, cq.message.id)
        return key, xoxo_games.get(key)

    # ---------------------- Handle board taps ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_\d$"))
    async def cb_xoxo_tap(_, cq: CallbackQuery):
        key, game = await _get_game(cq)
        if not game:
            # If challenge still exists, ignore. If nothing, expired.
            return await cq.answer("⚠️ This game is no longer active.", show_alert=True)

        if not cq.from_user or cq.from_user.is_bot:
            return await cq.answer()

        if game.get("finished"):
            return await cq.answer("Game already finished.", show_alert=True)

        try:
            idx = int(cq.data.split("_")[1])
        except (IndexError, ValueError):
            return await cq.answer()

        board = game["board"]
        if idx < 0 or idx >= len(board):
            return await cq.answer()

        # Cell already taken
        if board[idx] != " ":
            return await cq.answer("That spot is already taken.", show_alert=True)

        current = game["current"]  # "X" or "O"
        user_id = cq.from_user.id

        # Turn validation
        if current == "X":
            if user_id != game["player_x_id"]:
                return await cq.answer("It's ❌'s turn.", show_alert=True)
        else:
            if user_id != game["player_o_id"]:
                return await cq.answer("It's ⭕'s turn.", show_alert=True)

        # Apply move
        board[idx] = current

        # Check outcome
        result = _check_winner(board)

        # -------------------- Game finished --------------------
        if result in ("X", "O", "draw"):
            game["finished"] = True
            bet = game["bet"]
            pot = game["pot"]
            px_name = game["player_x_name"]
            po_name = game["player_o_name"]
            px_id = game["player_x_id"]
            po_id = game["player_o_id"]

            if result == "draw":
                # Refund both
                try:
                    ux = get_user(px_id)
                    uo = get_user(po_id)
                    if ux:
                        update_user(px_id, {"bronze": int(ux.get("bronze", 0)) + bet})
                    if uo:
                        update_user(po_id, {"bronze": int(uo.get("bronze", 0)) + bet})
                except Exception:
                    pass

                text = (
                    "❌⭕ <b>XO XO — Game Over</b>\n\n"
                    f"❌ <b>X:</b> {px_name}\n"
                    f"⭕ <b>O:</b> {po_name}\n"
                    f"💰 <b>Bet:</b> <code>{bet}</code> 🥉 each (Pot: <code>{pot}</code> 🥉)\n\n"
                    "🤝 It's a <b>draw</b>.\n"
                    "Both players have been refunded their bet.\n\n"
                    "Start a new match with /xoxo."
                )

                await cq.message.edit_text(
                    text,
                    reply_markup=_build_board_markup(board, finished=True),
                )
                xoxo_games.pop(key, None)
                return await cq.answer("Draw!")

            # There is a winner
            winner_symbol = result
            winner_id = px_id if winner_symbol == "X" else po_id
            winner_name = px_name if winner_symbol == "X" else po_name
            winner_emoji = _symbol_to_emoji(winner_symbol)

            # Give pot to winner
            try:
                uw = get_user(winner_id)
                if uw:
                    update_user(winner_id, {"bronze": int(uw.get("bronze", 0)) + pot})
            except Exception:
                pass

            text = (
                "❌⭕ <b>XO XO — Game Over</b>\n\n"
                f"❌ <b>X:</b> {px_name}\n"
                f"⭕ <b>O:</b> {po_name}\n"
                f"💰 <b>Bet:</b> <code>{bet}</code> 🥉 each (Pot: <code>{pot}</code> 🥉)\n\n"
                f"🏆 Winner: {winner_emoji} <b>{winner_name}</b>\n"
                "The entire pot has been awarded to the winner.\n\n"
                "Start a new match with /xoxo."
            )

            await cq.message.edit_text(
                text,
                reply_markup=_build_board_markup(board, finished=True),
            )
            xoxo_games.pop(key, None)
            return await cq.answer("Game over!")

        # -------------------- Game continues --------------------
        # Switch turn
        game["current"] = "O" if current == "X" else "X"
        next_symbol = game["current"]

        if next_symbol == "X":
            next_emoji = "❌"
            next_name = game["player_x_name"]
        else:
            next_emoji = "⭕"
            next_name = game["player_o_name"]

        bet = game["bet"]
        pot = game["pot"]
        px_name = game["player_x_name"]
        po_name = game["player_o_name"]

        text = (
            "❌⭕ <b>XO XO — Ongoing Match</b>\n\n"
            f"❌ <b>X:</b> {px_name}\n"
            f"⭕ <b>O:</b> {po_name}\n"
            f"💰 <b>Bet:</b> <code>{bet}</code> 🥉 each (Pot: <code>{pot}</code> 🥉)\n\n"
            f"Turn: {next_emoji} <b>{next_name}</b>\n"
            "Tap a square to play."
        )

        await cq.message.edit_text(
            text,
            reply_markup=_build_board_markup(board),
        )
        await cq.answer()

    # ---------------------- Finished board tap ----------------------
    @bot.on_callback_query(filters.regex(r"^xoxo_done$"))
    async def cb_xoxo_done(_, cq: CallbackQuery):
        await cq.answer("Game already finished. Start a new one with /xoxo.")
        # No further action

    print("[loaded] games.xoxo")
