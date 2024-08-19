import logging
from telegram import Message
from src.ai.gpt_formatter import format_message_with_gpt
from src.data.docsend_extract import extract_docsend_content, extract_text_from_pdf
from src.data.deal_counter import get_next_deal_id
import os
import shutil
from config import CSV_FIELDNAMES
from src.data.csv_writer import save_to_csv
import asyncio

async def extract_details(message: Message, bot):
    try:        
        combined_text = ""
        # Aggregate text from the original Telegram message
        if message.text:
            combined_text = message.text

        # Process the initial blurb with GPT to extract key fields
        content_dict = format_message_with_gpt(message_text=combined_text, expected_fields=None, mode='format')

        # Set hardcoded values and create the initial CSV entry
        deal_id = get_next_deal_id()
        forwarded_from = get_message_source(message)
        cmt_owner = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        account_name = content_dict.get('Account Name / PortCo', deal_id)

        content_dict.update({
            'Deal ID': deal_id,
            'Created Date': message.date.strftime("%Y-%m-%d"),
            'Record Type ID': "012Dm0000012ZYDIA2",
            'Stage': "New",
            'CMT Relationship Owner': cmt_owner,
            'Sharepoint Link': "",
            'Deal Source': None,
            'Forwarded From': forwarded_from,
            'File Name': message.document.file_name if message.document else ""
        })

        await save_to_csv(content_dict)

        # Background task for processing DocSend links and PDF documents
        docsend_links = extract_docsend_links(message)
        if docsend_links:
            asyncio.create_task(process_docsend_links(docsend_links, email='ojaros@cmt.digital', passcode='', combined_text=combined_text, content_dict=content_dict, account_name=account_name, deal_id=deal_id))
        
        # Background task for processing attached PDF documents (if any)
        if message.document:
            asyncio.create_task(process_document_attachment(message.document, bot, content_dict, account_name, combined_text))

        return {
            field: content_dict.get(field, '') for field in CSV_FIELDNAMES
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
    if hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
        return f"{message.forward_origin.sender_user.first_name} {message.forward_origin.sender_user.last_name or ''}".strip()
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
    """Extracts DocSend links from the message, looking in both the text and entities."""
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


async def process_docsend_links(docsend_links, email, passcode, combined_text, content_dict, account_name, deal_id):
    tasks = []
    pdf_paths = []
    for link in docsend_links:
        tasks.append(process_single_docsend_link(link, email, passcode, combined_text, content_dict, account_name, deal_id, pdf_paths))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

async def process_single_docsend_link(link, email, passcode, combined_text, content_dict, account_name, deal_id, pdf_paths):
    try:
        docsend_text, docsend_pdf_paths = await extract_docsend_content(link, email=email, passcode=passcode)
        combined_text += "\n" + docsend_text
        pdf_paths.extend(docsend_pdf_paths)

        # Update the CSV file with more detailed information from aggregated text
        update_csv_with_aggregated_text(combined_text, content_dict, account_name, deal_id, pdf_paths)
    except Exception as e:
        logging.error(f"Failed to process DocSend link {link}: {e}")


async def process_document_attachment(document, bot, content_dict, account_name, combined_text):
    try:
        file_path = await download_file(document, 'temp_pdfs/', bot)
        extracted_text = extract_text_from_pdf(file_path)
        combined_text += "\n" + extracted_text
        pdf_paths = [file_path]

        update_csv_with_aggregated_text(combined_text, content_dict, account_name, content_dict['Deal ID'], pdf_paths)

    except Exception as e:
        logging.error(f"Failed to process document attachment: {e}")

async def update_csv_with_aggregated_text(aggregated_text, content_dict, account_name, deal_id, pdf_paths):
    try:
        # Extract updated fields based on the aggregated text
        updated_content_dict = format_message_with_gpt(message_text=aggregated_text, expected_fields=None, mode='format')
        
        # Update the content dictionary with the most comprehensive information
        content_dict.update(updated_content_dict)
        content_dict['Deal ID'] = deal_id
        await save_to_csv(content_dict)

        # Move the processed PDFs to the account-specific directory
        if pdf_paths:
            move_pdfs_to_account_directory(account_name, pdf_paths)
            
    except Exception as e:
        logging.error(f"Failed to update CSV with aggregated text: {e}")
