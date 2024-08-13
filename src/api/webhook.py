import logging
from quart import Quart, request
from telegram import Update

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_app(application):
    app = Quart(__name__)

    @app.route(f'/{application.bot.token}', methods=['POST'])
    async def webhook():
        try:
            update = Update.de_json(await request.get_json(), application.bot)
            await application.process_update(update)
            logging.info('Update processed')
        except Exception as e:
            logging.error(f"Error handling webhook: {e}")
        return 'OK'

    return app

async def set_webhook(url, application):
    webhook_url = f"{url}/{application.bot.token}"
    try:
        await application.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logging.error(f"Exception while setting webhook: {e}")