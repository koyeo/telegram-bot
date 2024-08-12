from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
import logging

def extract_details(message: Message):
    formatted_content = format_message_with_gpt(message.text, message.date.strftime("%Y-%m-%d"))
    if not formatted_content:
        logging.error("Formatted content is None")
        return None

    logging.info(f"Formatted content: {formatted_content}")

    content_dict = {}
    for line in formatted_content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
        else:
            key = line.strip()
            value = ''
        content_dict[key.strip()] = value.strip()
    
    logging.info(f"Parsed content_dict: {content_dict}")

    cmt_owner = f"{message.from_user.first_name} {message.from_user.last_name}"
    
    return {
        'Deal ID': content_dict.get('- Deal ID', ''),
        'Description': content_dict.get('- Description', ''),
        'Website': content_dict.get('- Website', ''),
        'Deck': content_dict.get('- Deck', ''),
        'Fundraise Amount($USD)': content_dict.get('- Fundraise Amount($USD)', ''),
        'Valuation': content_dict.get('- Valuation', ''),
        'Date': content_dict.get('- Date', message.date.strftime("%Y-%m-%d")),
        'CMT Owner': cmt_owner
    }
