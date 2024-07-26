import logging
from telegram import Update
from telegram.ext import CallbackContext
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv

async def handle_message(update: Update, context: CallbackContext):
    message = update.message
    if message and message.text:
        try:
            logging.info(f"Received message: {message.text}")
            details = extract_details(message)
            save_to_csv(details)
            await message.reply_text("Investment details received, processed, and saved.")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            await message.reply_text("An error occurred while processing your message. Please ensure it contains investment details.")
    else:
        await message.reply_text("Please send a text message with investment details.")
