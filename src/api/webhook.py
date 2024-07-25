import asyncio
import logging
from flask import Flask, request
from telegram import Update
from src.bot.telegram_bot import setup_bot
from src.bot.message_handler import handle_message

app = Flask(__name__)
bot = setup_bot()

logging.basicConfig(level=logging.DEBUG)

@app.route(f'/{bot.token}', methods=['POST'])
def webhook():
    logging.info('Webhook called')
    logging.debug(f"Request headers: {request.headers}")
    logging.debug(f"Request data: {request.data}")
    try:
        update = Update.de_json(request.get_json(), bot)
        logging.debug(f"Update: {update}")
        asyncio.run(handle_message(update, None))
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
    return 'OK'

async def set_webhook(url):
    webhook_url = f"{url}/{bot.token}"
    success = await bot.set_webhook(webhook_url)
    if success:
        logging.info(f"Webhook set to {webhook_url}")
    else:
        logging.error("Failed to set webhook")
