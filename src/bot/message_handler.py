import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot

bot = setup_bot()

async def handle_message(update: Update, context):
    logging.info("handle_message started")
    message = update.message

    if message and message.text:
        if message.text.startswith('/'):
            logging.info("Command received, skipping handle_message")
            return  # Ignore commands in this handler

        source = "Unknown"
        if hasattr(message, 'forward_sender_name') and message.forward_sender_name:
            source = f"{message.forward_sender_name}"
        elif hasattr(message, 'forward_from') and message.forward_from:
            source = f"{message.forward_from.first_name} {message.forward_from.last_name or ''}".strip()
        elif hasattr(message, 'forward_origin') and message.forward_origin:
            if hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
                source = f"{message.forward_origin.sender_user.first_name} {message.forward_origin.sender_user.last_name or ''}".strip()
            elif hasattr(message.forward_origin, 'sender_user_name') and message.forward_origin.sender_user_name:
                source = f"{message.forward_origin.sender_user_name}"

        details = extract_details(message)
        if details:
            details['Source'] = source
            await save_to_csv(details)
            await context.bot.send_message(chat_id=message.chat_id, text="Investment details received, processed, and saved.")
            logging.info(f"Details saved to CSV with source: {source}")
        else:
            await context.bot.send_message(chat_id=message.chat_id, text="Error processing investment details. Please try again later.")
            logging.error("Error: Details were not extracted.")
    else:
        await context.bot.send_message(chat_id=message.chat_id, text="Please send a text message with investment details.")
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
