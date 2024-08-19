import logging
from quart import Quart, request
from telegram import Update
import asyncio
import time
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

processed_update_ids = {}

def create_app(application):
    app = Quart(__name__)

    @app.route(f'/{application.bot.token}', methods=['POST'])
    async def webhook():
        try:
            update_data = await request.get_json()
            update = Update.de_json(update_data, application.bot)

            update_hash = hashlib.sha256(f"{update.update_id}{time.time()}".encode()).hexdigest()

            if update.update_id in processed_update_ids:
                logging.info(f"Duplicate update received: {update.update_id}, ignoring.")
                return 'Duplicate', 200

            processed_update_ids[update.update_id] = update_hash

            if len(processed_update_ids) > 1000:
                processed_update_ids.popitem()

            asyncio.create_task(application.process_update(update))
            logging.info(f'Update {update.update_id} processed')
            return 'OK', 200

        except Exception as e:
            logging.error(f"Error handling webhook: {e}")
            return 'Internal Server Error', 500

    return app



async def set_webhook(url, application):
    webhook_url = f"{url}/{application.bot.token}"
    try:
        await application.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logging.error(f"Exception while setting webhook: {e}")