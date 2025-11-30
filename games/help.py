# File: GameBot/games/help.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import traceback

# ==========================================================
# 📌 FULL HELP TEXT (also used by /start deep-link)
# ==========================================================
FULL_HELP_TEXT = (
    "⚙️ ● <b><i>HELP CENTER</i></b>\n\n"

    "⟡ <b><i>Profile</i></b>\n"
    "• /start — Begin Your Journey\n"
    "• /profile — View Your Profile\n"
    "• /leaderboard — Top Players\n\n"

    "⟡ <b><i>Games</i></b>\n"
    "• /flip — Coin Flip Duel\n"
    "• /roll — Dice Roll\n"
    "• /fight — Fight Another Player\n"
    "• /rob — Rob a Player (Risk + Reward)\n"
    "• /spin — Try Your Luck on Spin Wheel\n"
    "• /guess — Guess the Hidden Word\n"
    "• /work — Earn Bronze Coins\n"
    "• /daily — Claim Daily Rewards (If /daily doesn't work, use /start and click on daily bonus)\n"
    "• /bet — Bet Coins and Multiply\n"
    "• /pay — Pay Coins to Another Player\n\n"

    "⟡ <b><i>Mining</i></b>\n"
    "• /mine — Mine Ores\n"
    "• /sell — Sell Your Mined Ores\n\n"

    "⟡ <b><i>Shop</i></b>\n"
    "• /shop — View Shop Items\n"
    "• /buy — Buy Items/Tools\n"
    "• /equip — Equip Purchased Tools\n\n"

    "⟡ <i>Tip: You Should Use These Commands In Group Chat "
    "For Better Performance.</i> ⚡️"
)


# ==========================================================
# 📌 HELP HANDLER
# ==========================================================
def init_help(bot: Client):

    @bot.on_message(filters.command(["help", "commands"]))
    async def help_cmd(_, msg: Message):
        try:
            group_help = (
                "⚙️ ● <b>HELP CENTER</b>\n\n"
                "⟡ <i>Tip: You Should Use These Commands In Bot's Personal Chat "
                "For Better Performance!</i> ⚡️"
            )

            me = await bot.get_me()
            deep_link = f"https://t.me/{me.username}?start=help"

            group_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📘 Help & Commands", url=deep_link)]]
            )

            # --------- FINAL, BULLETPROOF PRIVATE DETECTION ----------
            chat_type = str(msg.chat.type).lower()
            PRIVATE = ("private" in chat_type)

            # --------- SEND HELP ----------
            if PRIVATE:
                await msg.reply_text(
                    FULL_HELP_TEXT,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            else:
                await msg.reply_text(
                    group_help,
                    parse_mode=ParseMode.HTML,
                    reply_markup=group_kb,
                    disable_web_page_preview=True
                )

        except Exception:
            traceback.print_exc()
            try:
                await msg.reply_text("⚠️ Failed to load help menu.")
            except:
                pass
