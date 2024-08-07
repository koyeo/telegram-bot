import asyncio
import os
from src.api.webhook import set_webhook, app

async def main():
    webhook_url = os.getenv("WEBHOOK_URL")
    await set_webhook(webhook_url)

if __name__ == '__main__':
    asyncio.run(main())
    app.run(host='0.0.0.0', port=5000)
