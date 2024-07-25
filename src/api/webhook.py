from flask import Flask, request
from telegram import Update
from src.bot.telegram_bot import setup_bot
from src.bot.message_handler import handle_message

app = Flask(__name__)
bot = setup_bot()

@app.route(f'/{bot.token}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    handle_message(update, None)
    return 'OK'

def set_webhook(url):
    webhook_url = f"{url}/{bot.token}"
    success = bot.set_webhook(webhook_url)
    if success:
        print(f"Webhook set to {webhook_url}")
    else:
        print("Failed to set webhook")