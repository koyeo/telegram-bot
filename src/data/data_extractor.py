import logging
import fitz  # PyMuPDF
import pytesseract
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
import os
import re
from urllib.parse import urlparse
from docsend import DocSend

async def extract_details(message: Message, bot):
    try:
        combined_text = ""
        
        if message.text:
            combined_text = message.text
            # Extract content from the DocSend link
            if "docsend.com" in message.text.lower():
                for word in message.text.split():
                    if "docsend.com" in word:
                        print("WORD : ", word)
                        combined_text += "\n" + extract_docsend_content(word)
        
        if message.document:
            # Extract text from the PDF document
            file_id = message.document.file_id
            file_path = await download_file(file_id, 'data/', bot)
            extracted_text = extract_text_from_pdf(file_path)
            os.remove(file_path)
            
            # Append extracted text from PDF to combined_text
            combined_text = extracted_text + "\n" + combined_text if combined_text else extracted_text
        
        formatted_content = format_message_with_gpt(combined_text)
        
        content_dict = {}
        if formatted_content:
            for line in formatted_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    content_dict[key.strip().replace('- ', '')] = value.strip()  # Normalize the keys

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

def extract_docsend_content(url):
    try:
        # Extract the unique identifier from the URL
        parsed_url = urlparse(url)
        docsend_key = re.search(r'/view/s/(\w+)', parsed_url.path).group(1)
        print(f"DocSend Key: {docsend_key}")  # Debugging

        # Initialize the DocSend object with the extracted key
        docsend_client = DocSend(docsend_key)
        # docsend_client.fetch_meta()
        docsend_client.authorize('ojaros@cmt.digital')
        # docsend_client.fetch_images()
        docsend_client.save_pdf('doc.pdf')
        # docsend_client.save_images('pages')
        # text_content = ""
        # for page in docsend_client.pages:
        #     print("DOCSEND PAGE: ", page)  # Debugging
        #     text_content += page.text + "\n"
        # return text_content
    except AttributeError as e:
        logging.error(f"Error extracting content from DocSend link: Attribute error - {e}")
        return "Error extracting content from DocSend link."
    except Exception as e:
        logging.error(f"Error extracting content from DocSend link: {e}")
        return "Error extracting content from DocSend link."

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
