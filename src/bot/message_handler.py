import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot

bot = setup_bot()

async def handle_message(update: Update, context):
    logging.info("handle_message started")
    message = update.message

    if message and (message.text or message.document):
        if message.text and message.text.startswith('/'):
            logging.info("Command received, skipping handle_message")
            return  # Ignore commands in this handler

        details = await extract_details(message, bot)
        if details:
            await save_to_csv(details)
            await context.bot.send_message(chat_id=message.chat_id, text="Deal details received, processed, and saved.")
            logging.info(f"Details saved to CSV")
        else:
            await context.bot.send_message(chat_id=message.chat_id, text="Error processing deal details. Please try again later.")
            logging.error("Error: Details were not extracted.")
    else:
        await context.bot.send_message(chat_id=message.chat_id, text="Please send a text message or document with deal details.")
    logging.info("handle_message completed")

async def export_csv(update: Update, context):
    logging.info("export_csv command received")
    chat_id = update.message.chat_id
    filepath = 'data/dealflow.csv'
    if os.path.exists(filepath):
        await context.bot.send_document(chat_id=chat_id, document=open(filepath, 'rb'))
        logging.info("CSV file sent successfully")
    else:
        await context.bot.send_message(chat_id=chat_id, text="No messages logged yet.")

def add_handlers(application: Application):
    logging.info("Adding handlers")
    application.add_handler(CommandHandler('export_csv', export_csv))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
