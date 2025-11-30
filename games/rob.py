from pyrogram import Client, filters
from pyrogram.types import Message
from database.mongo import get_user, update_user
from utils.cooldown import check_cooldown, update_cooldown
import random, asyncio


def init_rob(bot: Client):

    @bot.on_message(filters.command("rob"))
    async def rob_cmd(_, msg: Message):

        # Must reply to a user in ANY chat (group or DM)
        if not msg.reply_to_message or not msg.reply_to_message.from_user:
            return await msg.reply("Reply to a user to rob them!")

        robber = msg.from_user
        victim = msg.reply_to_message.from_user

        if not robber:
            return
        if robber.id == victim.id:
            return await msg.reply("You cannot rob yourself.")

        robber_data = get_user(robber.id)
        victim_data = get_user(victim.id)

        # Cooldown: 5 minutes
        ok, wait, pretty = check_cooldown(robber_data, "rob", 300)
        if not ok:
            return await msg.reply(f"⏳ You must wait **{pretty}** before robbing again.")

        rob_msg = await msg.reply("🕵️ Trying to rob...")
        await asyncio.sleep(1)

        # Determine what victim has available
        chances = []
        if victim_data.get("bronze", 0) > 0:
            chances.append(("bronze", 100))
        if victim_data.get("silver", 0) > 0:
            chances.append(("silver", 80))
        if victim_data.get("gold", 0) > 0:
            chances.append(("gold", 50))
        if victim_data.get("platinum", 0) > 0:
            chances.append(("platinum", 10))

        # Victim has nothing
        if not chances:
            new_cd = update_cooldown(robber_data, "rob")
            update_user(robber.id, {"cooldowns": new_cd})
            return await rob_msg.edit("😶 Target has **no coins** to steal.")

        # Weighted selection of coin type
        tier_list = [t for t, _ in chances]
        weight_list = [w for _, w in chances]
        chosen_tier = random.choices(tier_list, weights=weight_list, k=1)[0]

        # Success chance
        success_chance = [w for t, w in chances if t == chosen_tier][0]
        if random.randint(1, 100) > success_chance:

            # FAILED robbery
            penalty = random.randint(1, 40)
            penalty = min(penalty, robber_data.get("bronze", 0))

            update_user(
                robber.id,
                {
                    "bronze": robber_data.get("bronze", 0) - penalty,
                    "rob_fail": robber_data.get("rob_fail", 0) + 1,
                    "cooldowns": update_cooldown(robber_data, "rob"),
                },
            )

            return await rob_msg.edit(
                f"🚨 **Robbery Failed!**\n"
                f"You lost **{penalty} Bronze 🥉**."
            )

        # SUCCESSFUL robbery
        victim_amount = victim_data.get(chosen_tier, 0)

        if chosen_tier == "bronze":
            steal = random.randint(1, min(60, victim_amount))
        elif chosen_tier == "silver":
            steal = random.randint(1, min(15, victim_amount))
        elif chosen_tier == "gold":
            steal = random.randint(1, min(5, victim_amount))
        else:  # platinum
            steal = 1

        # Update values
        update_user(
            robber.id,
            {
                chosen_tier: robber_data.get(chosen_tier, 0) + steal,
                "rob_success": robber_data.get("rob_success", 0) + 1,
                "cooldowns": update_cooldown(robber_data, "rob"),
            },
        )

        update_user(
            victim.id,
            {
                chosen_tier: max(0, victim_amount - steal)
            },
        )

        tier_emoji = {
            "bronze": "🥉",
            "silver": "🥈",
            "gold": "🥇",
            "platinum": "🏅",
        }[chosen_tier]

        await rob_msg.edit(
            f"💰 **Robbery Successful!**\n"
            f"You stole **{steal} {tier_emoji} {chosen_tier.capitalize()}** "
            f"from **{victim.first_name}**!"
        )
