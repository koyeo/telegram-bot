import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot

bot = setup_bot()

# Define the expected fields
EXPECTED_FIELDS = [
    'Deal ID', 'Account Name / PortCo', 'Deal Name', 'Stage', 'Account Description',
    'Website', 'Deck', 'Fundraise Amount($USD)', 'Equity Valuation/Cap', 'Token Valuation',
    'Round', 'Deal Source'
]

async def handle_message(update: Update, context):
    logging.info("handle_message started")
    message = update.message

    if message and (message.text or message.document):
        if message.text and message.text.startswith('/'):
            logging.info("Command received, skipping handle_message")
            return  # Ignore commands in this handler

        details = await extract_details(message, bot)
        if details:
            missing_fields = [field for field in EXPECTED_FIELDS if not details.get(field)]
            
            await save_to_csv(details)
            
            if missing_fields:
                missing_fields_str = ", ".join(missing_fields)
                response = f"Deal details processed and saved, but the following fields were missing or empty: {missing_fields_str}"
            else:
                response = "All deal details successfully received, processed, and saved."
            
            await context.bot.send_message(chat_id=message.chat_id, text=response)
            logging.info(f"Details saved to CSV. Missing fields: {missing_fields}")
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