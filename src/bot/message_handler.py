import logging
from telegram import Update
from telegram.ext import CallbackContext
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot
from tenacity import retry, stop_after_attempt, wait_exponential

bot = setup_bot()

# Define the expected fields
EXPECTED_FIELDS = [
    'Deal ID', 'Account Name / PortCo', 'Deal Name', 'Stage', 'Account Description',
    'Website', 'Deck', 'Fundraise Amount($USD)', 'Equity Valuation/Cap', 'Token Valuation',
    'Round', 'Deal Source'
]

# Retry configuration to avoid timeouts with multiple messages
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def send_message_with_retry(context: CallbackContext, chat_id: int, text: str):
    await context.bot.send_message(chat_id=chat_id, text=text)


async def handle_message(update: Update, context: CallbackContext):
    logging.info("handle_message started")
    message = update.message

    if message and (message.text or message.document):
        if message.text and message.text.startswith('/'):
            logging.info("Command received, skipping handle_message")
            return  # Ignore commands in this handler

        details = await extract_details(message, context.bot)
        if details:
            missing_fields = [field for field in EXPECTED_FIELDS if not details.get(field)]
            
            await save_to_csv(details)
            
            if missing_fields:
                missing_fields_str = "\n".join(missing_fields)  # Join each field with a newline
                response = (
                    f"Deal details processed and saved, but missing these fields:\n\n{missing_fields_str}"
                )
            else:
                response = "All deal details successfully received, processed, and saved."
            
            await send_message_with_retry(context, message.chat_id, response)
            logging.info(f"Details saved to CSV. Missing fields: {missing_fields}")
        else:
            await send_message_with_retry(context, message.chat_id, "Error processing deal details. Please try again later.")
            logging.error("Error: Details were not extracted.")
    else:
        await send_message_with_retry(context, message.chat_id, "Please send a text message or document with deal details.")
    
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