from pyrogram import Client, filters
from database.mongo import get_user, update_user

def init_pay(bot: Client):

    @bot.on_message(filters.command("pay"))
    async def pay_cmd(_, msg):
        user_id = msg.from_user.id
        user = get_user(user_id)

        # Must be a reply
        if not msg.reply_to_message:
            return await msg.reply("⚠ To pay someone, reply to their message and type: /pay <amount>")

        receiver = msg.reply_to_message.from_user
        receiver_id = receiver.id

        if receiver_id == user_id:
            return await msg.reply("❌ You can't pay yourself.")

        args = msg.text.split()
        if len(args) < 2:
            return await msg.reply("⚠ Usage: reply to a user and send /pay <amount>")

        # Validate amount
        try:
            amount = int(args[1])
        except:
            return await msg.reply("❌ Amount must be a number.")

        if amount <= 0:
            return await msg.reply("❌ Minimum payment is 1 coin.")

        sender_coins = user.get("bronze", 0)
        if sender_coins < amount:
            return await msg.reply(f"💰 You only have {sender_coins} bronze coins.\nYou can't send {amount}.")

        # Receiver DB fetch
        receiver_user = get_user(receiver_id)
        if not receiver_user:
            return await msg.reply("⚠ Receiver has no profile yet. Ask them to /start first.")

        # Update DB
        update_user(user_id, {"bronze": sender_coins - amount})
        update_user(receiver_id, {"bronze": receiver_user.get("bronze", 0) + amount})

        await msg.reply(
            f"💸 **Transaction Successful!**\n\n"
            f"👤 Sender: {msg.from_user.first_name}\n"
            f"👤 Receiver: {receiver.first_name}\n"
            f"💰 Amount: {amount} bronze coins\n"
            f"📦 New Balance (You): {sender_coins - amount}"
        )

    print("[loaded] games.pay")
