import logging
from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
from src.data.docsend_extract import extract_docsend_content, extract_text_from_pdf
from src.data.deal_counter import get_next_deal_id
import os
import shutil
import json

async def extract_details(message: Message, bot):
    try:
        combined_text = ""
        pdf_paths = []  # Collect PDF paths here
        
        # Aggregate text from the original Telegram message
        if message.text:
            combined_text = message.text
            
        docsend_links = extract_docsend_links(message)

        for link in docsend_links:
            docsend_text, docsend_pdf_paths = await extract_docsend_content(link, email='ojaros@cmt.digital', passcode='')
            combined_text += "\n" + docsend_text
            pdf_paths.extend(docsend_pdf_paths)

        # Handle attached PDF documents
        if message.document:
            file_path = await download_file(message.document, 'temp_pdfs/', bot)
            extracted_text = extract_text_from_pdf(file_path)
            combined_text += "\n" + extracted_text
            pdf_paths.append(file_path)  # Collect the PDF path

        logging.info(f"COMBINED TEXT: {combined_text[:1000]}")
        content_dict = format_message_with_gpt(message_text=combined_text, expected_fields=None, mode='format')
        
        logging.info(f"CONTENT DICT: {content_dict}")

        forwarded_from = get_message_source(message)
        cmt_owner = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        deal_id = get_next_deal_id()
        account_name = content_dict.get('Account Name / PortCo', deal_id)

        # Move PDFs to the account-specific directory if there are any PDFs
        if pdf_paths:
            move_pdfs_to_account_directory(account_name, pdf_paths)
            
        return {
            'Deal ID': deal_id,
            'Created Date': message.date.strftime("%Y-%m-%d"),
            'Account Name / PortCo': account_name,
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
            'Deal Source': None,
            'Forwarded From': forwarded_from,
            'File Name': message.document.file_name if message.document else ""
        }, None
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        logging.error(error_message)
        return None, error_message
    

async def download_file(document, save_path, bot):
    os.makedirs(save_path, exist_ok=True)
    file_name = document.file_name
    file = await bot.get_file(document.file_id)
    file_path = os.path.join(save_path, file_name)
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

def move_pdfs_to_account_directory(account_name, pdf_paths):
    """Move PDF files to the account-specific directory, avoiding duplicates, and clean up temporary files."""
    account_dir = os.path.join('account_pdfs', account_name)
    os.makedirs(account_dir, exist_ok=True)
    
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            file_name = os.path.basename(pdf_path)
            target_path = os.path.join(account_dir, file_name)
            
            if os.path.exists(target_path):
                logging.info(f"File {file_name} already exists in {account_dir}, deleting temporary file.")
                os.remove(pdf_path)
            else:
                shutil.move(pdf_path, target_path)
                logging.info(f"Moved {pdf_path} to {target_path}")
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logging.info(f"Deleted processed file: {pdf_path}")

def extract_docsend_links(message: Message) -> list:
    """
    Extracts DocSend links from the message, looking in both the text and entities.
    """
    docsend_links = []

    if message.text:
        words = message.text.split()
        for word in words:
            if "docsend.com" in word.lower():
                docsend_links.append(word)

    if message.entities:
        for entity in message.entities:
            if entity.type == "text_link" and "docsend.com" in entity.url.lower():
                docsend_links.append(entity.url)

    if message.caption_entities:
        for entity in message.caption_entities:
            if entity.type == "text_link" and "docsend.com" in entity.url.lower():
                docsend_links.append(entity.url)

    return docsend_links