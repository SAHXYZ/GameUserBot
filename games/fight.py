from pyrogram import Client, filters
from pyrogram.types import Message
import random
import asyncio

from database.mongo import get_user, update_user
from utils.cooldown import check_cooldown, update_cooldown


def init_fight(bot: Client):

    @bot.on_message(filters.command("fight"))
    async def fight_cmd(_, msg: Message):

        # Must be a reply to someone
        if not msg.reply_to_message or not msg.reply_to_message.from_user:
            return await msg.reply("Reply to a user to start a fight!")

        attacker = msg.from_user
        defender = msg.reply_to_message.from_user

        if attacker.id == defender.id:
            return await msg.reply("You cannot fight yourself!")

        atk = get_user(attacker.id)
        dfd = get_user(defender.id)

        # cooldown = 1 minute
        ok, wait, pretty = check_cooldown(atk, "fight", 60)
        if not ok:
            return await msg.reply(f"⏳ You must wait **{pretty}** before fighting again.")

        # Animations
        fmsg = await msg.reply("⚔️ **Fight Started...**")
        await asyncio.sleep(1)
        await fmsg.edit("🥊 Swinging punches...")
        await asyncio.sleep(1)
        await fmsg.edit("🔥 Final strike loading...")
        await asyncio.sleep(1)

        # Fight power system
        atk_b = atk.get("bronze", 0)
        dfd_b = dfd.get("bronze", 0)

        atk_power = atk_b + random.randint(20, 140)
        dfd_power = dfd_b + random.randint(20, 140)

        # -------------------
        # Attacker WINS
        # -------------------
        if atk_power >= dfd_power:

            steal = random.randint(10, 80)
            steal = min(steal, dfd_b)

            new_atk_bronze = atk_b + steal
            new_dfd_bronze = max(0, dfd_b - steal)

            update_user(attacker.id, {
                "bronze": new_atk_bronze,
                "fight_wins": atk.get("fight_wins", 0) + 1,
                "cooldowns": update_cooldown(atk, "fight"),
            })

            update_user(defender.id, {
                "bronze": new_dfd_bronze
            })

            return await fmsg.edit(
                f"🏆 **{attacker.first_name} Won the Fight!**\n\n"
                f"🥉 You stole **{steal} Bronze** from **{defender.first_name}**!"
            )

        # -------------------
        # Defender WINS
        # -------------------
        else:

            penalty = random.randint(5, 60)
            penalty = min(penalty, atk_b)

            new_atk_bronze = max(0, atk_b - penalty)
            new_dfd_bronze = dfd_b + penalty

            update_user(attacker.id, {
                "bronze": new_atk_bronze,
                "cooldowns": update_cooldown(atk, "fight"),
            })

            update_user(defender.id, {
                "bronze": new_dfd_bronze,
                "fight_wins": dfd.get("fight_wins", 0) + 1
            })

            return await fmsg.edit(
                f"😢 **You Lost the Fight!**\n\n"
                f"➖ You lost **{penalty} Bronze**.\n"
                f"🏆 **{defender.first_name}** gained **{penalty} Bronze**!"
            )
