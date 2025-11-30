# File: GameBot/games/start.py

# ==========================================================
# 🚫 Prevent accidental double-loading
# ==========================================================
if "start_loaded" in globals():
    raise SystemExit
start_loaded = True

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import traceback

from database.mongo import get_user, create_user_if_not_exists

# ==========================================================
# 📌 START TEXT (DM Home Page)
# ==========================================================
START_TEXT = (
    "Hᴇʏ {name}\n\n"
    "✧༺━━━༻✧༺━━━༻✧\n"
    "     ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɢᴀᴍᴇʙᴏᴛ\n"
    "✧༺━━━༻✧༺━━━༻✧\n\n"
    "● ʏᴏᴜ'ᴠᴇ sᴛᴇᴘᴘᴇᴅ ɪɴᴛᴏ ᴀ ᴘʀɪᴍᴇ-ᴛɪᴇʀ ᴅɪɢɪᴛᴀʟ ʀᴇᴀʟᴍ ~\n"
    "ғᴀsᴛᴇʀ. ʙᴏʟᴅᴇʀ. sᴍᴀʀᴛᴇʀ. ᴜɴᴅᴇɴɪᴀʙʟʏ sᴇxɪᴇʀ.\n\n"
    "✦ ᴇᴠᴇʀʏ ᴄʟɪᴄᴋ ɪɢɴɪᴛᴇs ᴘᴏᴡᴇʀ\n"
    "✦ ᴇᴠᴇʀʏ ᴄʜᴏɪᴄᴇ ᴄʀᴀғᴛs ʏᴏᴜʀ ʟᴇɢᴇɴᴅ\n"
    "✦ ᴇᴠᴇʀʏ ᴍᴏᴠᴇ ʟᴇᴀᴠᴇs ᴀ ᴍᴀʀᴋ\n\n"
    "ʟᴇᴠᴇʟ ᴜᴘ. ᴅᴏᴍɪɴᴀᴛᴇ. ᴄᴏɴǫᴜᴇʀ ᴛʜᴇ ɢʀɪᴅ.\n\n"
    "✧༺ ʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ɴᴇxᴛ ᴅᴇsᴛɪɴʏ… ༻✧\n\n"
    "◆ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @PrimordialEmperor ◆"
)

# ==========================================================
# 📌 MAIN MENU (DM Only)
# ==========================================================
def get_start_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="open_daily")],
        [InlineKeyboardButton("👤 Profile", callback_data="open_profile")],
        [InlineKeyboardButton("🏆 Leaderboards", callback_data="open_leaderboard")],
    ])

# ==========================================================
# 📌 Safe Editor
# ==========================================================
async def safe_edit(message, text, markup=None):
    try:
        if markup:
            return await message.edit_text(text, reply_markup=markup)
        return await message.edit_text(text)
    except:
        return

# ==========================================================
# 📌 START HANDLER (Group + DM)
# ==========================================================
def init_start(bot: Client):

    @bot.on_message(filters.command("start"))
    async def start_cmd(_, msg: Message):
        try:
            create_user_if_not_exists(msg.from_user.id, msg.from_user.first_name)

            args = msg.command[1:] if len(msg.command) > 1 else []

            # /start help
            if args and args[0].lower() == "help":
                from games.help import FULL_HELP_TEXT
                await msg.reply_text(
                    FULL_HELP_TEXT,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                return

            # /start daily (deep-link reward)
            if args and args[0].lower() == "daily":
                from games.daily import daily_reward
                await daily_reward(msg.from_user.id, msg)
                return

            bot_me = await _.get_me()

            # ======================================================
            # 📌 BULLETPROOF PRIVATE DETECTION
            # ======================================================
            chat_type = str(msg.chat.type).lower()
            PRIVATE = ("private" in chat_type)

            if PRIVATE:
                await msg.reply(
                    START_TEXT.format(name=msg.from_user.first_name),
                    reply_markup=get_start_menu()
                )
                return

            # ======================================================
            # 📌 GROUP CHAT → Short Intro + Button to DM
            # ======================================================
            start_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Start Here",
                    url=f"https://t.me/{bot_me.username}?start=menu"
                )]
            ])

            await msg.reply(
                f"Hello {msg.from_user.first_name},\n"
                "I’m a Gaming Bot!\n"
                "But even I am not aware of all my features yet. Will you help me discover them? 👇",
                reply_markup=start_btn
            )

        except Exception:
            traceback.print_exc()
            try:
                await msg.reply("⚠️ Error while starting the bot.")
            except:
                pass

    # ======================================================
    # 📌 HELP CENTER BUTTON
    # ======================================================
    @bot.on_callback_query(filters.regex("^help_show$"))
    async def help_show(_, q):
        try:
            commands_text = (
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
                "⟡ <i>Tip: You Should Use These Commands In Group Chat For Better Performance.</i> ⚡️"
            )

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]
            ])

            await safe_edit(q.message, commands_text, kb)
            await q.answer()
        except:
            traceback.print_exc()

    # ======================================================
    # 📌 BACK TO HOME BUTTON
    # ======================================================
    @bot.on_callback_query(filters.regex("^back_to_home$"))
    async def back_to_home(_, q):
        await safe_edit(
            q.message,
            START_TEXT.format(name=q.from_user.first_name),
            get_start_menu()
        )
        await q.answer()

    print("[loaded] games.start")
