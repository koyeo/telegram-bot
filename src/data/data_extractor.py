import logging
from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
from src.data.docsend_extract import extract_docsend_content, extract_text_from_pdf
import os

async def extract_details(message: Message, bot):
    try:
        combined_text = ""
        
        # Aggregate text from the original Telegram message
        if message.text:
            combined_text = message.text
            
            # Check for DocSend links in the message text
            if "docsend.com" in message.text.lower():
                for word in message.text.split():
                    if "docsend.com" in word:
                        print("WORD : ", word)
                        docsend_text = extract_docsend_content(word, email='ojaros@cmt.digital')
                        combined_text += "\n" + docsend_text

        # Handle attached PDF documents
        if message.document:
            file_id = message.document.file_id
            file_path = await download_file(file_id, 'data/', bot)
            extracted_text = extract_text_from_pdf(file_path)
            os.remove(file_path)
            
            # Aggregate extracted text from PDF with existing text
            combined_text += "\n" + extracted_text

        # logging.info(f"COMBINED TEXT:    {combined_text}  ")
        # Use GPT to format the aggregated content
        formatted_content = format_message_with_gpt(combined_text)

        # Parse the formatted content into a dictionary
        content_dict = parse_formatted_content(formatted_content)

        logging.info(f"CONTENT DICT: {content_dict}")

        source = get_message_source(message)
        cmt_owner = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

        return {
            'Deal ID': content_dict.get('Deal ID', ''),
            'Created Date': message.date.strftime("%Y-%m-%d"),
            'Account Name / PortCo': content_dict.get('Account Name / PortCo', ''),
            'Record Type ID': "012Dm0000012ZYDIA2",
            'Deal Name': content_dict.get('Deal Name', ''),
            'Stage': content_dict.get('Stage', 'New'),
            'Account Description': content_dict.get('Account Description', ''),
            'Website': content_dict.get('Website', ''),
            'Deck': content_dict.get('Deck', ''),
            'Fundraise Amount($USD)': content_dict.get('Fundraise Amount($USD)', ''),
            'Equity Valuation/Cap': content_dict.get('Equity Valuation/Cap', ''),
            'Token Valuation': content_dict.get('Token Valuation', ''),
            'CMT Relationship Owner': cmt_owner,
            'Sharepoint Link': "",
            'Round': content_dict.get('Round', ''),
            'Deal Source': source,
            'File Name': message.document.file_name if message.document else ""
        }
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        logging.error(error_message)
        await bot.send_message(chat_id=message.chat_id, text=error_message)
        return None

def parse_formatted_content(formatted_content):
    """Parse the formatted content returned by GPT into a dictionary."""
    content_dict = {}
    if formatted_content:
        for line in formatted_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                content_dict[key.strip().replace('- ', '')] = value.strip()
    return content_dict

async def download_file(file_id, save_path, bot):
    file = await bot.get_file(file_id)
    file_path = os.path.join(save_path, file.file_path.split('/')[-1])
    await file.download_to_drive(file_path)
    return file_path

def get_message_source(message: Message) -> str:
    """Extract the source of the forwarded message, if any."""
    if hasattr(message, 'forward_sender_name') and message.forward_sender_name:
        return message.forward_sender_name
    if hasattr(message, 'forward_from') and message.forward_from:
        return f"{message.forward_from.first_name} {message.forward_from.last_name or ''}".strip()
    if hasattr(message, 'forward_origin') and message.forward_origin:
        if hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
            return f"{message.forward_origin.sender_user.first_name} {message.forward_origin.sender_user.last_name or ''}".strip()
        if hasattr(message.forward_origin, 'sender_user_name') and message.forward_origin.sender_user_name:
            return message.forward_origin.sender_user_name
    return "Unknown"
