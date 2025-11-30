# ============================
# guess.py  (Part 1 / 3)
# ============================
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
import json
import random
import os
import time
from typing import Optional
from database.mongo import get_user, update_user

# ==========================================================
# Paths for word JSONs
# ==========================================================
ASSETS_DIR = os.path.join("games", "assets")
EASY_PATH = os.path.join(ASSETS_DIR, "Easy.json")
MEDIUM_PATH = os.path.join(ASSETS_DIR, "Medium.json")
HARD_PATH = os.path.join(ASSETS_DIR, "Hard.json")

# Optional local override directory (for local testing)
LOCAL_OVERRIDE_DIR = "games/asset"
LOCAL_EASY = os.path.join(LOCAL_OVERRIDE_DIR, "Easy.json")
LOCAL_MEDIUM = os.path.join(LOCAL_OVERRIDE_DIR, "Medium.json")
LOCAL_HARD = os.path.join(LOCAL_OVERRIDE_DIR, "Hard.json")


def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_path(repo_path: str, local_path: str) -> str:
    """
    Prefer local override file if present (for local testing).
    Otherwise use repo path (games/assets/*.json).
    """
    if os.path.exists(local_path):
        return local_path
    return repo_path


def get_words():
    """
    Dynamically load current JSON files so updated Easy/Medium/Hard
    are always used without full restart.
    """
    words = {
        "easy": load_json(resolve_path(EASY_PATH, LOCAL_EASY)),
        "medium": load_json(resolve_path(MEDIUM_PATH, LOCAL_MEDIUM)),
        "hard": load_json(resolve_path(HARD_PATH, LOCAL_HARD)),
    }
    return words


# Attempts per difficulty
ATTEMPTS_BY_DIFF = {
    "easy": 8,
    "medium": 7,
    "hard": 6,
}

# Hint limits per difficulty
HINT_LIMITS = {
    "easy": 2,
    "medium": 3,
    "hard": 4,
}

HINT_COST = 20  # Bronze per hint

# Attempt-based penalty per difficulty (for reward)
ATTEMPT_PENALTY = {
    "easy": 2,
    "medium": 3,
    "hard": 5,
}

# ==========================================================
# Game state
# ==========================================================
# state per chat_id:
# {
#   "difficulty": str,
#   "word": str,
#   "hint": dict,
#   "starter_id": int,
#   "answer_mode": bool,
#   "started_at": float,
#   "attempts_used": int,
#   "max_attempts": int,
#   "history": [ { "guess": str, "feedback": str }, ... ],
#   "hints_used": int,
#   "hints": [ "🟥L🟥🟥🟥", ... ]
# }
chats = {}

# Anti-spam per user (last answer timestamp)
_last_answer = {}


def pick_random_word(category: str):
    WORDS = get_words()
    pool = WORDS.get(category, {}) or {}
    if not pool:
        return None, None
    word = random.choice(list(pool.keys()))
    return word, pool[word]  # hint is a dict: meaning (+ maybe example)


def buttons_markup():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Easy", callback_data="guess_easy"),
                InlineKeyboardButton("Medium", callback_data="guess_medium"),
                InlineKeyboardButton("Hard", callback_data="guess_hard"),
            ]
        ]
    )


def quiz_control_markup():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Answer", callback_data="guess_answer"),
                InlineKeyboardButton("New", callback_data="guess_new"),
                InlineKeyboardButton("🛑 Stop", callback_data="guess_stop"),
            ]
        ]
    )


def hint_buy_markup():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"💡 Buy Hint ({HINT_COST} Bronze 🥉)",
                    callback_data="guess_buy_hint",
                )
            ]
        ]
    )


# ========== HINT / MEANING FORMAT HELPERS ==========

def pretty_hint(_: dict, length: int, max_attempts: Optional[int] = None):
    """
    Shown at quiz start:
    ONLY letters + attempts. No meaning / example.
    """
    base = f"Letters: {length}"
    if max_attempts is not None:
        base += f"\nAttempts: {max_attempts}"
    return base


def extract_example(hint: dict) -> str:
    """
    Extract only the example sentence for display at quiz start.
    """
    if isinstance(hint, dict):
        return hint.get("example", "") or ""
    return ""


def extract_meaning(hint: dict) -> str:
    """
    Extract meaning text from hint dict.
    Called only after 5+ attempts.
    """
    if isinstance(hint, dict):
        meaning = hint.get("meaning") or ""
        return str(meaning)
    return str(hint)


def build_meaning_block(hint: dict) -> str:
    meaning = extract_meaning(hint).strip()
    if not meaning:
        return ""
    return f"\n\n📘 **Meaning Hint:**\n> {meaning}"


# ========== REWARD HELPERS ==========

def reward_for_difficulty(diff: str) -> int:
    """
    Base random reward before applying attempt penalty.
    """
    if diff == "easy":
        return random.randint(20, 50)
    if diff == "medium":
        return random.randint(40, 100)
    return random.randint(80, 150)


def compute_final_reward(diff: str, attempts_used: int) -> int:
    """
    Reward decreases slightly as attempts increase.
    Minimum reward = 5 Bronze.
    """
    base = reward_for_difficulty(diff)
    penalty = ATTEMPT_PENALTY.get(diff, 2)
    extra = max(0, attempts_used - 1)  # first attempt = no penalty
    reward = base - extra * penalty
    if reward < 5:
        reward = 5
    return reward


# ========== CORE GAME HELPERS ==========

def can_answer(user_id: int, cooldown_seconds: int = 2) -> bool:
    now = time.time()
    last = _last_answer.get(user_id, 0)
    if now - last < cooldown_seconds:
        return False
    _last_answer[user_id] = now
    return True


def compute_feedback(guess: str, target: str) -> str:
    """
    Wordle-style feedback:
    🟩 correct letter + correct position
    🟨 exists but wrong position
    🟥 not in word
    """
    guess = guess.lower()
    target = target.lower()

    target_chars = list(target)

    # First pass: correct positions
    marks = [""] * len(guess)
    for i, ch in enumerate(guess):
        if i < len(target) and ch == target[i]:
            marks[i] = "🟩"
            target_chars[i] = None  # consume

    # Second pass: present / absent
    for i, ch in enumerate(guess):
        if marks[i] == " 🟩":
            continue
        if ch in target_chars:
            marks[i] = " 🟨"
            idx = target_chars.index(ch)
            target_chars[idx] = None
        else:
            marks[i] = " 🟥"

    return "".join(marks)


def build_history_block(history: list, hints: Optional[list] = None) -> str:
    """
    WordSeek-style layout (aligned):

    🟥🟥🟩🟥🟥   𝗣𝗟𝗔𝗬𝗦
    🟥🟨🟥🟥🟥   𝗚𝗟𝗢𝗥𝗬
    🟥🟥🟥🟥🟥   𝗕𝗥𝗢𝗪𝗡
    🟥L🟥🟥🟥
    """
    lines = []

    # Use triple spaces to prevent Telegram collapsing spacing on mobile.
    SPACER = "   "  # 3 spaces for better alignment

    for item in history:
        feedback = item["feedback"]
        word = item["guess"]

        # Bold sans-serif effect for tighter, consistent width on devices
        fancy = "".join(
            [chr(ord(c) + 0x1D5EE - 0x41) if "A" <= c <= "Z" else c for c in word]
        )

        lines.append(f"{feedback}{SPACER}{fancy}")

    if hints:
        for h in hints:
            lines.append(h)

    return "\n".join(lines)


def max_hints_for_diff(diff: str) -> int:
    return HINT_LIMITS.get(diff, 2)


def build_single_letter_hint(target: str) -> str:
    """
    Return a string like:
    🟥L🟥🟥🟥  (one correct letter revealed at a random position)
    """
    if not target:
        return ""

    length = len(target)
    idx = random.randint(0, length - 1)
    chars = []
    for i in range(length):
        if i == idx:
            chars.append(target[i].upper())
        else:
            chars.append(" 🟥")
    return "".join(chars)
# ============================
# guess.py  (Part 2 / 3)
# ============================

# ==========================================================
# Main init
# ==========================================================
def init_guess(bot: Client):

    # ---------------------- /guess ----------------------
    @bot.on_message(filters.command("guess"))
    async def cmd_guess(_, msg: Message):
        chat_id = str(msg.chat.id)
        if chat_id in chats and chats[chat_id].get("word"):
            return await msg.reply("A quiz is already running here. Use the buttons or /stop.")
        await msg.reply("**Choose difficulty:**", reply_markup=buttons_markup())

    # ---------------------- difficulty selected ----------------------
    @bot.on_callback_query(filters.regex(r"^guess_(easy|medium|hard)$"))
    async def difficulty_selected(_, cq: CallbackQuery):
        chat_id = str(cq.message.chat.id)
        difficulty = cq.data.split("_")[1]

        if chat_id in chats and chats[chat_id].get("word"):
            return await cq.answer("A quiz is already running.", show_alert=True)

        word, hint = pick_random_word(difficulty)
        if not word:
            return await cq.answer("❌ No words found.", show_alert=True)

        max_attempts = ATTEMPTS_BY_DIFF.get(difficulty, 6)
        example = extract_example(hint)

        chats[chat_id] = {
            "difficulty": difficulty,
            "word": word,
            "hint": hint,
            "starter_id": cq.from_user.id if cq.from_user else None,
            "answer_mode": False,
            "started_at": time.time(),
            "attempts_used": 0,
            "max_attempts": max_attempts,
            "history": [],
            "hints_used": 0,
            "hints": [],
        }

        text = (
            f"**New Quiz — {difficulty.title()} Mode**\n\n"
            f"{pretty_hint(hint, len(word), max_attempts)}"
        )

        if example:
            text += f"\n\n💬 **Example:** _{example}_"

        text += (
            "\n\nUse the buttons:\n"
            "Answer — enable answering\n"
            "New — new word\n"
            "Stop — end quiz"
        )

        await cq.message.edit_text(text, reply_markup=quiz_control_markup())
        await cq.answer()

    # ---------------------- enable answer ----------------------
    @bot.on_callback_query(filters.regex(r"^guess_answer$"))
    async def cb_enable_answer(_, cq: CallbackQuery):
        chat_id = str(cq.message.chat.id)
        state = chats.get(chat_id)

        if not state:
            return await cq.answer("❌ No active quiz.", show_alert=True)

        if state["answer_mode"]:
            return await cq.answer("📝 Already enabled.", show_alert=True)

        state["answer_mode"] = True
        await cq.answer("📝 Answer mode ON!")

    # ---------------------- new word ----------------------
    @bot.on_callback_query(filters.regex(r"^guess_new$"))
    async def cb_new_word(_, cq: CallbackQuery):
        chat_id = str(cq.message.chat.id)
        state = chats.get(chat_id)

        if not state:
            return await cq.answer("❌ No active quiz.", show_alert=True)

        difficulty = state["difficulty"]
        word, hint = pick_random_word(difficulty)
        if not word:
            return await cq.answer("❌ No more words.", show_alert=True)

        max_attempts = ATTEMPTS_BY_DIFF.get(difficulty, 6)
        example = extract_example(hint)

        state.update({
            "word": word,
            "hint": hint,
            "answer_mode": False,
            "attempts_used": 0,
            "max_attempts": max_attempts,
            "history": [],
            "hints_used": 0,
            "hints": [],
        })

        text = (
            f"🔎 **New Hint — {difficulty.title()} Mode**\n\n"
            f"{pretty_hint(hint, len(word), max_attempts)}"
        )

        if example:
            text += f"\n\n**Example:** _{example}_"

        text += "\n\nPress Answer to start guessing."

        await cq.message.edit_text(text, reply_markup=quiz_control_markup())
        await cq.answer()

    # ---------------------- stop quiz ----------------------
    @bot.on_callback_query(filters.regex(r"^guess_stop$"))
    async def cb_stop_quiz(_, cq: CallbackQuery):
        chat_id = str(cq.message.chat.id)
        state = chats.get(chat_id)

        if not state:
            return await cq.answer("❌ No active quiz.", show_alert=True)

        starter = state.get("starter_id")
        if cq.from_user and starter and cq.from_user.id != starter:
            return await cq.answer("Only the user who started the quiz can stop it.", show_alert=True)

        chats.pop(chat_id, None)
        try:
            await cq.message.edit("**Quiz stopped.**")
        except Exception:
            pass
        await cq.answer()

    # ---------------------- /answer command ----------------------
    @bot.on_message(filters.command("answer"))
    async def enable_answer_cmd(_, msg: Message):
        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)

        if not state or not state.get("word"):
            return await msg.reply("❌ No active quiz.")
        if state["answer_mode"]:
            return await msg.reply("📝 Answer mode already ON.")
        state["answer_mode"] = True
        await msg.reply("📝 **Answer mode ON!** Send your guesses now.")

    # ---------------------- /new command ----------------------
    @bot.on_message(filters.command("new"))
    async def new_word_cmd(_, msg: Message):
        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)

        if not state:
            return await msg.reply("❌ No active quiz running.")

        difficulty = state["difficulty"]
        word, hint = pick_random_word(difficulty)
        if not word:
            return await msg.reply("❌ No more words available.")

        max_attempts = ATTEMPTS_BY_DIFF.get(difficulty, 6)
        example = extract_example(hint)

        state.update({
            "word": word,
            "hint": hint,
            "attempts_used": 0,
            "answer_mode": False,
            "max_attempts": max_attempts,
            "history": [],
            "hints_used": 0,
            "hints": [],
        })

        text = (
            f"🔎 **New Hint — {difficulty.title()} Mode**\n\n"
            f"{pretty_hint(hint, len(word), max_attempts)}"
        )

        if example:
            text += f"\n\n💬 **Example:** _{example}_"

        await msg.reply(text, reply_markup=quiz_control_markup())

    # ---------------------- /hint command ----------------------
    @bot.on_message(filters.command("hint"))
    async def hint_cmd(_, msg: Message):
        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)

        if not state or not state.get("word"):
            return await msg.reply("❌ No active quiz to hint for.")

        difficulty = state["difficulty"]
        hints_used = state.get("hints_used", 0)
        max_hints = max_hints_for_diff(difficulty)

        if hints_used >= max_hints:
            return await msg.reply(
                f"🚫 You have used all hints for this quiz.\n"
                f"💡 Allowed hints for **{difficulty.title()}**: {max_hints}"
            )

        await msg.reply(
            f"🔍 Do you want to buy a hint for **{HINT_COST} Bronze 🥉**?\n"
            f"Difficulty: **{difficulty.title()}**\n"
            f"Hints used: **{hints_used}/{max_hints}**",
            reply_markup=hint_buy_markup()
        )
# ============================
# guess.py  (Part 3 / 3)
# ============================

    # ---------------------- hint purchase button ----------------------
    @bot.on_callback_query(filters.regex(r"^guess_buy_hint$"))
    async def cb_buy_hint(_, cq: CallbackQuery):
        chat_id = str(cq.message.chat.id)
        user_id = cq.from_user.id if cq.from_user else None
        if not user_id:
            return await cq.answer("Unknown user.", show_alert=True)

        state = chats.get(chat_id)
        if not state or not state.get("word"):
            return await cq.answer("❌ No active quiz.", show_alert=True)

        difficulty = state["difficulty"]
        hints_used = state.get("hints_used", 0)
        max_hints = max_hints_for_diff(difficulty)

        if hints_used >= max_hints:
            return await cq.answer(
                f"🚫 Hint limit reached ({hints_used}/{max_hints}).",
                show_alert=True,
            )

        # Check user bronze
        try:
            user = get_user(user_id)
            current_bronze = int(user.get("bronze", 0))
        except Exception:
            current_bronze = 0

        if current_bronze < HINT_COST:
            return await cq.answer(
                f"Not enough Bronze. You need {HINT_COST} Bronze 🥉.",
                show_alert=True,
            )

        # Deduct cost
        try:
            update_user(user_id, {"bronze": current_bronze - HINT_COST})
        except Exception:
            return await cq.answer("Database error, try again later.", show_alert=True)

        # Mark hint used
        hints_used += 1
        state["hints_used"] = hints_used

        correct = state["word"]
        history = state.get("history", [])
        hints = state.setdefault("hints", [])

        # Build visual hint row
        hint_row = build_single_letter_hint(correct)
        hints.append(hint_row)

        # Build combined block (guesses + hint rows)
        history_block = build_history_block(history, hints)

        text = (
            f"{history_block}\n\n"
            "🟩 correct • 🟨 present • 🟥 absent"
        )

        await cq.message.reply(text)
        await cq.answer("Hint purchased!")

    # ---------------------- Only handle guesses when quiz active ----------------------
    def quiz_active_filter(_, __, msg: Message) -> bool:
        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)
        return bool(state and state.get("word") and state.get("answer_mode"))

    quiz_active = filters.create(quiz_active_filter)

    # ---------------------- process guesses ----------------------
    @bot.on_message(
        filters.text
        & ~filters.command(["guess", "answer", "new", "stop", "convert", "hint"])
        & quiz_active,
        group=1,
    )
    async def process_answer(_, msg: Message):
        if not msg.from_user or msg.from_user.is_bot:
            return

        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)
        if not state:
            return

        if not can_answer(msg.from_user.id):
            return await msg.reply("⏳ Slow down — you're answering too fast.")

        guess = msg.text.strip().lower()
        correct = state["word"].lower()
        difficulty = state["difficulty"]
        attempts_used = state.get("attempts_used", 0)
        max_attempts = state["max_attempts"]
        hint_data = state.get("hint", {})

        # Length check
        if len(guess) != len(correct):
            return await msg.reply(
                f"❌ Your guess must be **{len(correct)}** letters."
            )

        # Dictionary validation
        pool = get_words().get(difficulty, {})
        if pool and guess not in pool:
            return await msg.reply("This Word Is Not Corrct Please Try another word.")

        # Update attempt counter
        attempts_used += 1
        state["attempts_used"] = attempts_used

        # Compute feedback & store history
        feedback = compute_feedback(guess, correct)
        history = state.setdefault("history", [])
        hints = state.get("hints", [])
        history.append({"guess": guess.upper(), "feedback": feedback})

        # Block showing guesses + hints
        full_history = build_history_block(history, hints)

        # Meaning only after 5+ attempts
        meaning_block = ""
        if attempts_used >= 5:
            meaning_block = build_meaning_block(hint_data)

        # ---------------- CORRECT GUESS ----------------
        if guess == correct:
            reward = compute_final_reward(difficulty, attempts_used)

            try:
                usr = get_user(msg.from_user.id)
                update_user(
                    msg.from_user.id,
                    {"bronze": usr.get("bronze", 0) + reward},
                )
            except Exception:
                pass

            winner = msg.from_user.mention
            guesses_only = build_history_block(history, hints=[])

            chats.pop(chat_id, None)

            text = (
                "🎉 **Correct!**\n"
                f"🏆 Winner: {winner}\n"
                f"🎯 Attempts: **{attempts_used}/{max_attempts}**\n"
                f"🎁 Reward: **{reward} Bronze 🥉**\n"
                "⚡ Faster guesses earn more reward!\n\n"
                f"{guesses_only}\n\n"
                "🟩 correct • 🟨 present • 🟥 absent"
            )

            if meaning_block:
                text += meaning_block

            text += "\n\n▶ Use /guess to start a new quiz!"
            return await msg.reply(text)

        # ---------------- OUT OF ATTEMPTS ----------------
        if attempts_used >= max_attempts:
            chats.pop(chat_id, None)

            text = (
                "**Out of attempts!**\n"
                f"🔚 The word was: `{correct.upper()}`\n\n"
                f"{full_history}\n\n"
                "🟩 correct • 🟨 present • 🟥 absent"
            )

            if meaning_block:
                text += meaning_block

            text += "\n\n▶ Use /guess to start a new quiz!"
            return await msg.reply(text)

        # ---------------- WRONG GUESS ----------------
        text = (
            "❌ **Not quite!**\n"
            f"🔢 Attempt: **{attempts_used}/{max_attempts}**\n\n"
            f"{full_history}\n\n"
            "🟩 correct • 🟨 present • 🟥 absent"
        )

        if meaning_block:
            text += meaning_block

        return await msg.reply(text)

    # ---------------------- /stop ----------------------
    @bot.on_message(filters.command("stop"))
    async def stop_quiz_cmd(_, msg: Message):
        chat_id = str(msg.chat.id)
        state = chats.get(chat_id)
        if not state:
            return await msg.reply("❌ No quiz is currently running.")
        starter = state.get("starter_id")
        if msg.from_user.id != starter:
            return await msg.reply("Only the user who started the quiz can stop it.")
        chats.pop(chat_id, None)
        await msg.reply("**Quiz stopped.**")

    # ---------------------- owner-only reload words ----------------------
    @bot.on_message(filters.command("reload_words") & filters.me)
    async def reload_words(_, msg: Message):
        _ = get_words()
        await msg.reply("**Word lists reloaded!**")
