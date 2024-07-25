from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt

def extract_details(message: Message):
    formatted_content = format_message_with_gpt(message.text, message.date.strftime("%Y-%m-%d"))
    
    # Parse the formatted content into a dictionary
    content_dict = {}
    for line in formatted_content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            content_dict[key.strip()] = value.strip()
    
    return {
        'Deal ID': content_dict.get('Deal ID', ''),
        'Description': content_dict.get('Description', ''),
        'Website': content_dict.get('Website', ''),
        'Deck': content_dict.get('Deck', ''),
        'Fundraise Amount($USD)': content_dict.get('Fundraise Amount($USD)', ''),
        'Valuation': content_dict.get('Valuation', ''),
        'Date': content_dict.get('Date', message.date.strftime("%Y-%m-%d"))
    }