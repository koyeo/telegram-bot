import asyncio
import os
from src.api.webhook import set_webhook, create_app
from telegram.ext import ApplicationBuilder
from src.bot.telegram_bot import setup_bot
from src.bot.message_handler import add_handlers

async def main():
    bot = setup_bot()
    application = ApplicationBuilder().token(bot.token).build()
    add_handlers(application)

    webhook_url = os.getenv("WEBHOOK_URL")
    await set_webhook(webhook_url, application)

    await application.initialize()
    await application.start()
    
    quart_app = create_app(application)
    
    port = int(os.getenv('PORT', 5000))
    await quart_app.run_task(host='0.0.0.0', port=port)

if __name__ == '__main__':
    asyncio.run(main())