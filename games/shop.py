# File: GameBot/games/shop.py

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from database.mongo import get_user, update_user


# ---------------------------------------
# SHOP DATA
# ---------------------------------------
ITEMS = [
    ("Lucky Charm", 200),
    ("Golden Key", 350),
    ("Magic Potion", 500),
    ("Royal Crown", 900),
]

TOOLS = [
    ("Wooden", 50),
    ("Stone", 150),
    ("Iron", 400),
    ("Platinum", 3000),
    ("Diamond", 8000),
    ("Emerald", 20000),
]


# ---------------------------------------
# KEYBOARDS
# ---------------------------------------
def main_shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Items", callback_data="shop_items")],
        [InlineKeyboardButton("🛠 Tools", callback_data="shop_tools")],
    ])


def items_keyboard():
    rows = []
    row = []

    for name, _ in ITEMS:
        row.append(InlineKeyboardButton(name, callback_data=f"buy_item:{name}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("⬅ Back", callback_data="shop_back")])
    return InlineKeyboardMarkup(rows)


def tools_keyboard():
    rows = []
    row = []

    for name, _ in TOOLS:
        row.append(InlineKeyboardButton(name, callback_data=f"buy_tool:{name}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("⬅ Back", callback_data="shop_back")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------
# PURCHASE HELPERS
# ---------------------------------------
async def purchase_item(msg, user, name, price):
    if user["bronze"] < price:
        return await msg.reply(
            f"❌ Not enough Bronze.\nNeeded: {price}\nYou have: {user['bronze']}"
        )

    user["bronze"] -= price
    user["inventory"]["items"].append(name)

    update_user(user["_id"], user)

    await msg.reply(
        f"✅ **Purchased:** {name}\n💰 Remaining Bronze: {user['bronze']}"
    )


async def purchase_tool(msg, user, name, price):

    if user["bronze"] < price:
        return await msg.reply(
            f"❌ Not enough Bronze.\nNeeded: {price}\nYou have: {user['bronze']}"
        )

    # Deduct bronze
    user["bronze"] -= price

    # Add tool to inventory list
    tools = user["inventory"].setdefault("tools", [])

    if name not in tools:
        tools.append(name)

    update_user(user["_id"], user)

    await msg.reply(
        f"🛠 **Purchased Tool:** {name}\n"
        f"Use `/equip` to equip your tools.\n"
        f"Remaining Bronze: {user['bronze']}"
    )


# ---------------------------------------
# INIT SHOP
# ---------------------------------------
def init_shop(bot: Client):

    # /shop
    @bot.on_message(filters.command("shop"))
    async def open_shop(_, msg: Message):

        user = get_user(msg.from_user.id)
        if not user:
            return await msg.reply("❌ Please use /start first.")

        # Ensure inventory structure exists
        user.setdefault("inventory", {})
        user["inventory"].setdefault("items", [])
        user["inventory"].setdefault("tools", [])
        user["inventory"].setdefault("ores", {})
        update_user(msg.from_user.id, user)

        await msg.reply(
            "🛒 **GAMEBOT SHOP**\nChoose a section:",
            reply_markup=main_shop_keyboard(),
        )

    # TEXT BUY
    @bot.on_message(filters.command("buy"))
    async def text_buy(_, msg: Message):

        if len(msg.text.split()) < 2:
            return await msg.reply("Usage:\n`/buy Golden Key`")

        query = msg.text.split(maxsplit=1)[1].strip().lower()
        user = get_user(msg.from_user.id)

        if not user:
            return await msg.reply("❌ Use /start first.")

        # Item matching
        for name, price in ITEMS:
            if name.lower() == query:
                return await purchase_item(msg, user, name, price)

        # Tool matching
        for name, price in TOOLS:
            if name.lower() == query:
                return await purchase_tool(msg, user, name, price)

        await msg.reply("❌ Item not found. Use /shop")

    # SECTION SWITCH
    @bot.on_callback_query(filters.regex("shop_items"))
    async def show_items(_, cq: CallbackQuery):
        await cq.message.edit_text(
            "⭐ **Items Store**\nChoose an item:",
            reply_markup=items_keyboard()
        )
        await cq.answer()

    @bot.on_callback_query(filters.regex("shop_tools"))
    async def show_tools(_, cq: CallbackQuery):
        await cq.message.edit_text(
            "🛠 **Tools Store**\nChoose a tool:",
            reply_markup=tools_keyboard()
        )
        await cq.answer()

    @bot.on_callback_query(filters.regex("shop_back"))
    async def shop_back(_, cq: CallbackQuery):
        await cq.message.edit_text(
            "🛒 **GAMEBOT SHOP**\nChoose a section:",
            reply_markup=main_shop_keyboard()
        )
        await cq.answer()

    # BUTTON PURCHASE — ITEMS
    @bot.on_callback_query(filters.regex(r"^buy_item:"))
    async def button_buy_item(_, cq: CallbackQuery):
        name = cq.data.split(":", 1)[1]
        price = next(p for n, p in ITEMS if n == name)

        user = get_user(cq.from_user.id)
        await purchase_item(cq.message, user, name, price)
        await cq.answer()

    # BUTTON PURCHASE — TOOLS
    @bot.on_callback_query(filters.regex(r"^buy_tool:"))
    async def button_buy_tool(_, cq: CallbackQuery):
        name = cq.data.split(":", 1)[1]
        price = next(p for n, p in TOOLS if n == name)

        user = get_user(cq.from_user.id)
        await purchase_tool(cq.message, user, name, price)
        await cq.answer()

    print("[loaded] games.shop")
