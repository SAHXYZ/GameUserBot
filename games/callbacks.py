# File: GameBot/games/callbacks.py

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
import traceback

from database.mongo import get_user, update_user

if "module_loaded" in globals():
    raise SystemExit
module_loaded = True


async def safe_edit(message, text, markup=None):
    """Edits message safely without crashing if already edited/deleted."""
    try:
        if markup:
            return await message.edit_text(text, reply_markup=markup)
        else:
            return await message.edit_text(text)
    except Exception:
        return


def init_callbacks(bot: Client):

    # ⬇️ IMPORTS MOVED INSIDE THE INITIALIZER
    from games.start import get_start_menu, START_TEXT
    from games.profile import build_profile_text_for_user, get_profile_markup
    from games.daily import daily_reward

    # For Word-Chain
    from games.wordchain import WORDSETS, games as wc_games

    # ===================== START / HOME =====================
    @bot.on_callback_query(filters.regex("^start_back$"))
    async def start_back(_, q: CallbackQuery):
        await safe_edit(
            q.message,
            START_TEXT.format(name=q.from_user.first_name),
            get_start_menu()
        )
        await q.answer()

    @bot.on_callback_query(filters.regex("^back_to_home$"))
    async def cb_back_home(_, q: CallbackQuery):
        await safe_edit(
            q.message,
            START_TEXT.format(name=q.from_user.first_name),
            get_start_menu()
        )
        await q.answer()

    # ===================== PROFILE =====================
    @bot.on_callback_query(filters.regex("^open_profile$"))
    async def cb_open_profile(_, q: CallbackQuery):
        user = get_user(q.from_user.id)
        if not user:
            return await q.answer("⚠ You have no profile. Use /start.")
        mention = getattr(q.from_user, "mention", q.from_user.first_name)
        text = build_profile_text_for_user(user, mention)
        await safe_edit(q.message, text, get_profile_markup())
        await q.answer()

    # ===================== DAILY REWARD =====================
    @bot.on_callback_query(filters.regex("^open_daily$"))
    async def cb_open_daily(_, q: CallbackQuery):
        await daily_reward(q.from_user.id, q.message)
        await q.answer()

    # ===================== LEADERBOARD =====================
    @bot.on_callback_query(filters.regex("^open_leaderboard$"))
    async def cb_open_leaderboard(_, q: CallbackQuery):
        from games.top import leaderboard_menu
        await safe_edit(q.message, "📊 **Choose a leaderboard type:**", leaderboard_menu())
        await q.answer()

    # ===================== SPIN GAME =====================
    @bot.on_callback_query(filters.regex("^spin_"))
    async def cb_spin_buttons(_, q: CallbackQuery):
        await q.answer()

    # ===================== WORD CHAIN GAME =====================
    @bot.on_callback_query(filters.regex("^wc_"))
    async def cb_wordchain(_, q: CallbackQuery):
        mode = q.data.replace("wc_", "")  # cities / nouns / animals / fruits / vegetables

        if mode not in WORDSETS:
            return await q.answer("Unknown category.", show_alert=True)

        # First word chosen by bot
        first_word = WORDSETS[mode][0]
        last_letter = first_word[-1].lower()

        wc_games[q.message.chat.id] = {
            "mode": mode,
            "last": last_letter,
            "used": {first_word.lower()}
        }

        await safe_edit(
            q.message,
            f"🎮 **Word Chain Game Started!**\n\n"
            f"Category: **{mode.capitalize()}**\n"
            f"Bot's word: **{first_word}**\n\n"
            f"➡️ Your turn! Send a word starting with **{last_letter.upper()}**"
        )

        await q.answer()

    print("[loaded] games.callbacks")
