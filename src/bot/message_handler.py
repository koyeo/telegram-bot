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
        try:
            logging.info(f"Received message: {message.text}")
            details = extract_details(message)
            logging.info(f"Extracted details: {details}")
            if details:
                try:
                    await save_to_csv(details)
                    logging.info("Details saved to CSV successfully.")
                except Exception as e:
                    logging.error(f"Error saving to CSV: {str(e)}")
                    await context.bot.send_message(chat_id=message.chat_id, text=f"Error saving to CSV: {str(e)}")
                    return

                try:
                    await context.bot.send_message(chat_id=message.chat_id, text="Investment details received, processed, and saved.")
                    logging.info("Reply sent: Investment details received, processed, and saved.")
                except Exception as e:
                    logging.error(f"Error sending message: {str(e)}")
                    await context.bot.send_message(chat_id=message.chat_id, text=f"Error sending message: {str(e)}")
                    return
            else:
                logging.error("Error: Details were not extracted.")
                await context.bot.send_message(chat_id=message.chat_id, text="Error processing investment details. Please try again later.")
                logging.info("Reply sent: Error processing investment details.")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            await context.bot.send_message(chat_id=message.chat_id, text=f"An error occurred while processing your message: {str(e)}")
            logging.info(f"Reply sent: An error occurred while processing your message: {str(e)}")
    else:
        await context.bot.send_message(chat_id=message.chat_id, text="Please send a text message with investment details.")
    logging.info("handle_message completed")

async def export_csv(update: Update, context):
    logging.info("export_csv command received")
    chat_id = update.message.chat_id
    # Check if the CSV file exists
    filepath = 'data/dealflow.csv'
    if os.path.exists(filepath):
        try:
            # Send the CSV file to the user
            await context.bot.send_document(chat_id=chat_id, document=open(filepath, 'rb'))
            logging.info("CSV file sent successfully")
        except Exception as e:
            logging.error(f"Error sending CSV file: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"Error sending CSV file: {str(e)}")
    else:
        logging.info("No messages logged yet")
        await context.bot.send_message(chat_id=chat_id, text="No messages logged yet.")

def add_handlers(application: Application):
    logging.info("Adding handlers")
    application.add_handler(CommandHandler('export_csv', export_csv))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
