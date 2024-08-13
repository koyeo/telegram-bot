from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
import logging

def extract_details(message: Message):
    formatted_content = format_message_with_gpt(message.text)
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

    print("MESSAGE: ", message)
    cmt_owner = f"{message.from_user.first_name} {message.from_user.last_name}"

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
    
    return {
        'Deal ID': "",
        'Created Date': message.date.strftime("%Y-%m-%d"),
        'Account Name / PortCo': content_dict.get('- Account Name / PortCo', ''),
        'Record Type ID': "012Dm0000012ZYDIA2",
        'Deal Name': content_dict.get('- Deal Name', ''),
        'Stage': content_dict.get('- Stage', ''),
        'Account Description': content_dict.get('- Account Description', ''),
        'Website': content_dict.get('- Website', ''),
        'Deck': content_dict.get('- Deck', ''),
        'Fundraise Amount($USD)': content_dict.get('- Fundraise Amount($USD)', ''),
        'Equity Valuation/Cap': content_dict.get('- Equity Valuation/Cap', ''),
        'Token Valuation': content_dict.get('- Token Valuation', ''),
        'CMT Relationship Owner': cmt_owner,
        'Sharepoint Link': "",
        'Round': content_dict.get('- Round', ''),
        'Deal Source': source
    }
