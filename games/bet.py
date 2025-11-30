from pyrogram import Client, filters
from database.mongo import get_user, update_user
import random
import time

BET_COOLDOWN = 7   # seconds
MIN_BET = 1        # minimum amount to bet

def init_bet(bot: Client):

    @bot.on_message(filters.command("bet"))
    async def bet_cmd(_, msg):
        user_id = msg.from_user.id
        user = get_user(user_id)

        args = msg.text.split()
        if len(args) < 2:
            return await msg.reply("⚠ Usage: /bet <amount>\nExample: /bet 100 or /bet *", quote=True)

        raw = args[1]
        coins = user.get("bronze", 0)

        # ----- NEW FEATURE: /bet * (bet all coins)
        if raw == "*":
            amount = coins
        else:
            try:
                amount = int(raw)
            except:
                return await msg.reply("❌ Amount must be a number or * to bet all.", quote=True)

        if amount < MIN_BET:
            return await msg.reply("❌ Minimum bet is 1 coin.", quote=True)

        if coins < amount:
            return await msg.reply(
                f"💰 You only have {coins} bronze coins.\nYou can't bet {amount}.",
                quote=True
            )

        # cooldown system
        last = user.get("last_bet", 0)
        now = int(time.time())
        remaining = last + BET_COOLDOWN - now
        if remaining > 0:
            return await msg.reply(
                f"⏳ Please wait {remaining}s before betting again.",
                quote=True
            )

        # 50/50 win or lose
        win = random.choice([True, False])

        if win:
            new_coins = coins + amount
            result = f"🎉 You won! You gained +{amount} bronze coins!"
        else:
            new_coins = coins - amount
            result = f"😢 You lost -{amount} bronze coins."

        update_user(user_id, {"bronze": new_coins, "last_bet": now})

        await msg.reply(
            f"🎲 Bet Result\n\n{result}\n\n💼 New Balance: {new_coins} bronze coins",
            quote=True
        )

    print("[loaded] games.bet")
