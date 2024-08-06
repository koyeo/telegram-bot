import logging
import asyncio
from quart import Quart, request
from telegram import Update
from src.bot.telegram_bot import setup_bot
from src.bot.message_handler import handle_message

app = Quart(__name__)
bot = setup_bot()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.route(f'/{bot.token}', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(await request.get_json(), bot)
        logging.debug(f"Update: {update}")
        await handle_message(update)
        logging.info('handle_message executed')
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
