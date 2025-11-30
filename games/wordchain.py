# File: games/wordchain.py

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Prevent double import
if "module_loaded_wordchain" in globals():
    raise SystemExit
module_loaded_wordchain = True

games = {}

# ======================= SAFE EDIT =======================

async def safe_edit(message, text, markup=None):
    try:
        if markup:
            return await message.edit_text(text, reply_markup=markup)
        else:
            return await message.edit_text(text)
    except:
        return


# ======================= AUTO WORD LISTS =======================

from geonamescache import GeonamesCache
gc = GeonamesCache()
CITIES = sorted({city["name"].lower() for city in gc.get_cities().values()})

from wordfreq import top_n_list

WORDLIST = top_n_list("en", n=50000)
WORDSET = set(WORDLIST)

NOUNS = [w for w in WORDLIST if len(w) > 2]

ANIMAL_SEEDS = {
    "lion", "tiger", "elephant", "cat", "dog", "rabbit", "cow", "goat", "monkey",
    "horse", "zebra", "giraffe", "bear", "wolf", "fox", "deer", "mouse", "rat",
    "sheep", "buffalo", "kangaroo", "panda", "hippo", "rhino", "camel", "donkey",
    "leopard", "cheetah", "squirrel", "bat", "otter", "duck", "eagle", "falcon",
    "frog", "snake", "turtle", "whale", "shark", "dolphin", "penguin"
}

FRUIT_SEEDS = {
    "apple", "banana", "mango", "orange", "grape", "kiwi", "papaya", "watermelon",
    "melon", "pear", "peach", "plum", "cherry", "pineapple", "strawberry",
    "blueberry", "blackberry", "raspberry", "apricot", "guava", "lychee"
}

VEG_SEEDS = {
    "potato", "tomato", "onion", "carrot", "spinach", "beans", "pea", "peas",
    "broccoli", "cabbage", "lettuce", "cauliflower", "cucumber", "pumpkin",
    "radish", "turnip", "garlic", "ginger", "chili", "pepper"
}

ANIMALS = sorted({w for w in WORDLIST if w in ANIMAL_SEEDS})
FRUITS = sorted({w for w in WORDLIST if w in FRUIT_SEEDS})
VEGETABLES = sorted({w for w in WORDLIST if w in VEG_SEEDS})

WORDSETS = {
    "cities": CITIES,
    "nouns": NOUNS,
    "animals": ANIMALS,
    "fruits": FRUITS,
    "vegetables": VEGETABLES,
}

# ======================= BOT HANDLERS =======================

def init_wordchain(bot: Client):

    # =================== /end ===================
    @bot.on_message(filters.command("end"), group=15)
    async def stop_game(_, message: Message):
        chat_id = message.chat.id

        if chat_id not in games:
            await message.reply("❌ No active Word Chain game to end.")
            return

        del games[chat_id]

        await message.reply("**Word Chain game ended.**\nYou can start again using \new.")

    # =================== SELECT CATEGORY ===================
    @bot.on_message(filters.command("new"), group=15)
    async def choose_category(_, message: Message):

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🏙 Cities", callback_data="wc_cities"),
                InlineKeyboardButton("📘 Nouns", callback_data="wc_nouns"),
            ],
            [
                InlineKeyboardButton("🐾 Animals", callback_data="wc_animals"),
                InlineKeyboardButton("🍎 Fruits", callback_data="wc_fruits"),
                InlineKeyboardButton("🥬 Vegetables", callback_data="wc_vegetables"),
            ]
        ])

        await message.reply(
            "Choose your Word-Chain category:",
            reply_markup=keyboard
        )

    # =================== START GAME ===================
    @bot.on_callback_query(filters.regex(r"wc_"), group=15)
    async def start_game(_, cq: CallbackQuery):

        mode = cq.data.replace("wc_", "")
        dataset = WORDSETS.get(mode, [])

        if not dataset:
            await cq.answer("No words available for this category.", show_alert=True)
            return

        import random
        first_word = random.choice(dataset)
        last_letter = first_word[-1]

        games[cq.message.chat.id] = {
            "mode": mode,
            "last": last_letter,
            "used": {first_word},
        }

        await safe_edit(
            cq.message,
            f"🎮 **Word Chain Game Started!**\n\n"
            f"Category: **{mode.capitalize()}**\n"
            f"Bot's word: **{first_word}**\n\n"
            f"➡️ Your turn! Send a word starting with **{last_letter.upper()}**"
        )

        await cq.answer()

    # =================== PLAYER RESPONSE ===================
    @bot.on_message(filters.text & ~filters.command(["new", "end"]), group=15)
    async def word_handler(_, message: Message):

        chat_id = message.chat.id
        if chat_id not in games:
            return

        user_word = message.text.strip().lower()
        state = games[chat_id]

        if not user_word.startswith(state["last"]):
            await message.reply(
                f"❌ Wrong letter!\n"
                f"Word must start with **{state['last'].upper()}**."
            )
            return

        dataset = WORDSETS[state["mode"]]

        if user_word not in dataset:
            await message.reply(
                f"❌ `{user_word}` is not in my {state['mode']} list."
            )
            return

        if user_word in state["used"]:
            await message.reply("❌ This word was already used.")
            return

        state["used"].add(user_word)
        next_letter = user_word[-1]
        state["last"] = next_letter

        await message.reply(
            f"✅ Correct!\n"
            f"Now send a word starting with **{next_letter.upper()}**."
        )
