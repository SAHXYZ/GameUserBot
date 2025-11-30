from pyrogram import Client, filters
from pyrogram.types import Message
from database.mongo import get_user, update_user
from utils.cooldown import check_cooldown, update_cooldown
import random
import asyncio

WORK_TASKS = [
    "Delivering parcels 📦",
    "Fixing a computer 🖥️",
    "Cleaning a mansion 🧹",
    "Helping at a store 🏪",
    "Repairing a car 🚗",
    "Cooking in a restaurant 🍳",
    "Gardening in the yard 🌱",
    "Tuning a bike 🚴",
]


def init_work(bot: Client):

    @bot.on_message(filters.command("work"))
    async def work_cmd(_, msg: Message):

        if not msg.from_user:
            return

        user_id = msg.from_user.id
        user = get_user(user_id)

        # Cooldown: 5 minutes
        ok, wait, pretty = check_cooldown(user, "work", 300)
        if not ok:
            return await msg.reply(f"⏳ You must wait **{pretty}** before working again.")

        # Pick random task
        task = random.choice(WORK_TASKS)
        working_msg = await msg.reply(f"🔧 You start: **{task}**\n⏳ Working...")

        await asyncio.sleep(1.2)

        # Reward System A (your choice): 1–100 Bronze
        reward = random.randint(1, 100)
        new_bronze = user.get("bronze", 0) + reward

        # Track work count for badges
        work_count = user.get("work_done", 0) + 1
        badges = user.get("badges", [])

        # Unlock badge at 20 jobs
        if work_count >= 20 and "🛠️" not in badges:
            badges.append("🛠️")  # Work Master badge

        # Update cooldown
        new_cd = update_cooldown(user, "work")

        # Update database
        update_user(
            user_id,
            {
                "bronze": new_bronze,
                "cooldowns": new_cd,
                "work_done": work_count,
                "badges": badges
            }
        )

        # Final edit
        try:
            await working_msg.edit(
                f"💼 **Work Completed!**\n"
                f"✨ You earned **{reward} Bronze** 🥉"
            )
        except:
            pass
