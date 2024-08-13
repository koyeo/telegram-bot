import logging
import fitz  # PyMuPDF
import pytesseract
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
import os
import numpy as np

async def extract_details(message: Message, bot):
    try:
        combined_text = ""
        
        if message.text:
            combined_text = message.text
        
        if message.document:
            # Extract text from the PDF document
            file_id = message.document.file_id
            file_path = await download_file(file_id, 'data/', bot)
            extracted_text = extract_text_from_pdf(file_path)
            os.remove(file_path)
            combined_text = extracted_text + "\n" + combined_text if combined_text else extracted_text
        
        formatted_content = format_message_with_gpt(combined_text)
        
        content_dict = {}
        if formatted_content:
            for line in formatted_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    content_dict[key.strip().replace('- ', '')] = value.strip()  # Normalize the keys
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

async def download_file(file_id, save_path, bot):
    file = await bot.get_file(file_id)
    file_path = os.path.join(save_path, file.file_path.split('/')[-1])
    await file.download_to_drive(file_path)
    return file_path

def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_page, page) for page in doc]
        for future in futures:
            text += future.result()
    return text

def process_page(page):
    page_text = page.get_text()
    if not page_text.strip():
        # If no text is found, use OCR as a fallback
        page_text = ocr_page(page)
    return page_text

def ocr_page(page):
    try:
        page_pix = page.get_pixmap()
        img = Image.frombytes("RGB", [page_pix.width, page_pix.height], page_pix.samples)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        logging.error(f"OCR processing error: {e}")
        return "Error performing OCR"

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
