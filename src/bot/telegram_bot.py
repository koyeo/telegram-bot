import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Updater
from telegram.request import HTTPXRequest

load_dotenv()

def setup_bot():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No token provided. Set TELEGRAM_BOT_TOKEN in .env file or environment.")
    
    request = HTTPXRequest(connection_pool_size=10)
    return Bot(token=token, request=request)

def get_updater():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("No token provided. Set TELEGRAM_BOT_TOKEN in .env file or environment.")
    
    request = HTTPXRequest(connection_pool_size=10)
    return Updater(token=token, request=request, use_context=True)
