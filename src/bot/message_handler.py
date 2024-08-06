import logging
from telegram import Update, Bot
from src.data.data_extractor import extract_details
from src.data.csv_writer import save_to_csv
import os
from src.bot.telegram_bot import setup_bot

bot = setup_bot()

async def handle_message(update: Update):
    logging.info("handle_message started")
    message = update.message
    if message and message.text:
        try:
            logging.info(f"Received message: {message.text}")
            details = extract_details(message)
            logging.info(f"Received details: {details}")
            if details:
                try:
                    await save_to_csv(details)
                    logging.info("Details saved to CSV successfully.")
                except Exception as e:
                    logging.error(f"Error saving to CSV: {str(e)}")
                    await bot.send_message(chat_id=message.chat_id, text=f"Error saving to CSV: {str(e)}")
                    return

                try:
                    await bot.send_message(chat_id=message.chat_id, text="Investment details received, processed, and saved.")
                    logging.info("Reply sent: Investment details received, processed, and saved.")
                except Exception as e:
                    logging.error(f"Error sending message: {str(e)}")
                    await bot.send_message(chat_id=message.chat_id, text=f"Error sending message: {str(e)}")
                    return
            else:
                logging.error("Error: Details were not extracted.")
                await bot.send_message(chat_id=message.chat_id, text="Error processing investment details. Please try again later.")
                logging.info("Reply sent: Error processing investment details.")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            await bot.send_message(chat_id=message.chat_id, text=f"An error occurred while processing your message: {str(e)}")
            logging.info(f"Reply sent: An error occurred while processing your message: {str(e)}")
    else:
        await bot.send_message(chat_id=message.chat_id, text="Please send a text message with investment details.")
    logging.info("handle_message completed")
