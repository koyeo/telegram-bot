import asyncio
from src.bot.telegram_bot import setup_bot
from src.api.webhook import set_webhook
import os


async def main():
    bot = setup_bot()
    webhook_url = os.getenv("WEBHOOK_URL")
    await set_webhook(webhook_url)

if __name__ == '__main__':
    asyncio.run(main())