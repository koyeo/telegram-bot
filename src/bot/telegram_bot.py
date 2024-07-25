import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Updater

load_dotenv()

def setup_bot():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No token provided. Set TELEGRAM_BOT_TOKEN in .env file or environment.")
    return Bot(token=token)

def get_updater():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No token provided. Set TELEGRAM_BOT_TOKEN in .env file or environment.")
    return Updater(token=token, use_context=True)