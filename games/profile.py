# File: GameBot/games/profile.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from database.mongo import get_user
from games.start import get_start_menu
import traceback


# --------------------------------------
# Total bronze value calculator
# --------------------------------------
def total_bronze_value(user: dict) -> int:
    black = int(user.get("black_gold", 0)) * 100000000
    plat  = int(user.get("platinum", 0)) * 1000000
    gold  = int(user.get("gold", 0)) * 10000
    sil   = int(user.get("silver", 0)) * 100
    bron  = int(user.get("bronze", 0))
    return black + plat + gold + sil + bron


# --------------------------------------
# BUILD PROFILE TEXT
# --------------------------------------
def build_profile_text_for_user(user: dict, mention: str):

    black_gold = int(user.get("black_gold", 0))
    platinum   = int(user.get("platinum", 0))
    gold       = int(user.get("gold", 0))
    silver     = int(user.get("silver", 0))
    bronze     = int(user.get("bronze", 0))
    total_val  = total_bronze_value(user)

    messages   = user.get("messages", 0)
    wins       = user.get("fight_wins", 0)
    rob_s      = user.get("rob_success", 0)
    rob_f      = user.get("rob_fail", 0)

    badges = " ".join(user.get("badges", [])) or "None"

    inv = user.get("inventory", {})
    ores = inv.get("ores", {})
    items = inv.get("items", [])

    ore_summary = ", ".join([f"{k}({v})" for k, v in ores.items()]) or "No ores"
    items_summary = ", ".join(items) or "No items"

    tools = user.get("tools", {})
    equipped = user.get("equipped") or "None"
    dur = user.get("tool_durabilities", {}).get(equipped, "N/A")

    text = (
        f"👤 **Profile of {mention}**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 **Currency**\n"
        f"🎖 Black Gold: `{black_gold}`\n"
        f"🏅 Platinum: `{platinum}`\n"
        f"🥇 Gold: `{gold}`\n"
        f"🥈 Silver: `{silver}`\n"
        f"🥉 Bronze: `{bronze}`\n"
        f"🔢 Total Value: `{total_val}`\n\n"

        f"📊 **Stats**\n"
        f"💬 Messages: `{messages}`\n"
        f"🥊 Fight Wins: `{wins}`\n"
        f"🕵️ Rob Success: `{rob_s}`\n"
        f"🚨 Rob Failures: `{rob_f}`\n\n"

        f"⛏️ **Mining**\n"
        f"🧰 Equipped Tool: `{equipped}`\n"
        f"🔧 Durability: `{dur}`\n\n"

        f"⛏️ Ores: {ore_summary}\n"
        f"🛒 Items: {items_summary}\n\n"

        f"🏅 **Badges:** {badges}\n"
    )

    return text


# --------------------------------------
# Profile Markup (buttons)
# --------------------------------------
def get_profile_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]
    ])


# --------------------------------------
# INIT PROFILE MODULE (This was missing)
# --------------------------------------
def init_profile(bot: Client):

    @bot.on_message(filters.command("profile"))
    async def profile_cmd(_, msg: Message):
        try:
            user = get_user(msg.from_user.id)
            if not user:
                return await msg.reply("❌ Use /start to create your profile first.")

            mention = msg.from_user.mention or msg.from_user.first_name
            text = build_profile_text_for_user(user, mention)

            await msg.reply(text, reply_markup=get_profile_markup())

        except Exception:
            traceback.print_exc()
            try:
                await msg.reply("⚠️ Couldn't load profile.")
            except:
                pass

    print("[loaded] games.profile")
