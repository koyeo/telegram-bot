from telegram import Update
from telegram.ext import CallbackContext
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv

def handle_message(update: Update, context: CallbackContext):
    message = update.message
    if message and message.text:
        try:
            details = extract_details(message)
            save_to_csv(details)
            message.reply_text("Investment details received, processed, and saved.")
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            message.reply_text("An error occurred while processing your message. Please ensure it contains investment details.")
    else:
        message.reply_text("Please send a text message with investment details.")