import logging
from telegram import Update
from telegram.ext import CallbackContext
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot
from src.ai.gpt_formatter import format_message_with_gpt
from tenacity import retry, stop_after_attempt, wait_exponential

bot = setup_bot()

# Define the expected fields
EXPECTED_FIELDS = [
    'Deal ID', 'Account Name / PortCo', 'Deal Name', 'Stage', 'Account Description',
    'Website', 'Deck', 'Fundraise Amount($USD)', 'Equity Valuation/Cap', 'Token Valuation',
    'Round', 'Deal Source'
]

missing_fields_tracker = {}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def send_message_with_retry(context: CallbackContext, chat_id: int, text: str, message_id: int):
    return await context.bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=message_id)

async def handle_message(update: Update, context: CallbackContext):
    logging.info("handle_message started")
    message = update.message

    if not message or (message.text and message.text.startswith('/')):
        logging.info("Command or empty message received, skipping handle_message")
        return

    details, error_message = await extract_details(message, context.bot)
    if not details:
        await send_message_with_retry(context, message.chat_id, f"Error processing deal details: {error_message}. Please try again later.", message.message_id)
        logging.error(f"Error: {error_message}")
        return

    missing_fields = [field for field in EXPECTED_FIELDS if not details.get(field)]
    await save_to_csv(details)
    
    if missing_fields:
        missing_fields_str = "\n".join(missing_fields)
        response = (
            f"Deal details processed and saved, but missing these fields:\n\n{missing_fields_str}"
        )
        bot_message = await send_message_with_retry(context, message.chat_id, response, message.message_id)
        missing_fields_tracker[bot_message.message_id] = {'details': details, 'missing_fields': missing_fields}
        logging.info(f"Stored missing fields for message ID {bot_message.message_id}.")
    else:
        await send_message_with_retry(context, message.chat_id, "All deal details successfully received, processed, and saved.", message.message_id)
        logging.info("Details saved to CSV successfully with no missing fields.")

    logging.info("handle_message completed")

async def handle_reply(update: Update, context: CallbackContext):
    logging.info("handle_reply started")
    message = update.message
    reply_to_message = message.reply_to_message

    if not (reply_to_message and reply_to_message.message_id in missing_fields_tracker):
        logging.info("No tracked message found for reply, skipping handle_reply")
        return

    tracked_info = missing_fields_tracker[reply_to_message.message_id]
    user_reply = message.text
    updated_fields = format_message_with_gpt(user_reply, tracked_info['missing_fields'], mode='parse')

    details = tracked_info['details']
    for field, value in updated_fields.items():
        if value:
            details[field] = value

    await save_to_csv(details)
    logging.info("Updated deal details saved to CSV.")

    remaining_missing_fields = [field for field in tracked_info['missing_fields'] if not details.get(field)]
    
    if remaining_missing_fields:
        missing_fields_str = "\n".join(remaining_missing_fields)
        response = (
            f"The deal details have been updated, but these fields are still missing: \n\n{missing_fields_str}\n\n Please reply with the remaining information."
        )
        missing_fields_tracker[reply_to_message.message_id]['missing_fields'] = remaining_missing_fields
    else:
        response = "All deal details successfully received, processed, and saved."
        del missing_fields_tracker[reply_to_message.message_id]

    await send_message_with_retry(context, message.chat_id, response, message.message_id)
    logging.info("handle_reply completed")


async def export_csv(update: Update, context):
    logging.info("export_csv command received")
    chat_id = update.message.chat_id
    filepath = 'data/dealflow.csv'
    if os.path.exists(filepath):
        await context.bot.send_document(chat_id=chat_id, document=open(filepath, 'rb'))
        logging.info("CSV file sent successfully")
    else:
        await context.bot.send_message(chat_id=chat_id, text="No messages logged yet.")