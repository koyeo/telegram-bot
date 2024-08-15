import requests
from bs4 import BeautifulSoup
import logging
import os
import fitz
from PIL import Image
import pytesseract
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json
import html
from functools import wraps
import shutil
import asyncio

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e} | Args: {args} | Kwargs: {kwargs}")
            return f"Error in {func.__name__}"
    return wrapper

@error_handler
async def extract_docsend_content(url, email, passcode=''):
    logging.info(f"Starting extraction for URL: {url}")
    session = create_session()
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    if 'input' in response.text and 'authenticity_token' in response.text:
        soup = authenticate(session, url, email, passcode, soup)

    pdf_paths = []

    if '/s/' in url:
        combined_text, temp_pdf_paths = await handle_dataroom(session, soup, email, passcode)
        pdf_paths.extend(temp_pdf_paths)
    else:
        extracted_text, temp_pdf_path = await handle_single_document(url, email, passcode)
        combined_text = extracted_text
        pdf_paths.append(temp_pdf_path)

    return combined_text, pdf_paths

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
    })
    return session

@error_handler
def authenticate(session, url, email, passcode, soup):
    csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
    auth_data = {
        'utf8': '✓', '_method': 'patch', 'authenticity_token': csrf_token,
        'link_auth_form[email]': email, 'link_auth_form[passcode]': passcode,
        'commit': 'Continue'
    }
    auth_response = session.post(url, data=auth_data)
    auth_response.raise_for_status()
    logging.info(f"Authenticated with email: {email}")
    return BeautifulSoup(auth_response.text, 'html.parser')

async def process_docsend_document(session, url, email, passcode, safe_doc_name):
    logging.info(f"Processing URL: {url}")

    document_text, temp_pdf_path = await handle_single_document(url, email, passcode, safe_doc_name)
    return document_text, temp_pdf_path

async def handle_dataroom(session, soup, email, passcode):
    doc_links = extract_document_links(soup)
    logging.info(f"Found {len(doc_links)} links in the dataroom.")

    tasks = []

    for link in doc_links:
        if 'href' in link.attrs:
            doc_url = link['href']
            doc_name_tag = link.find('div', class_='bundle-document_name')
            doc_name = doc_name_tag.text.strip() if doc_name_tag else "unknown_document"
            safe_doc_name = re.sub(r'[^\w\-_\.]', '_', doc_name).replace(' ', '_')
            
            if is_valid_docsend_document(session, doc_url):
                tasks.append(asyncio.create_task(process_docsend_document(session, doc_url, email, passcode, safe_doc_name)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    combined_text = ""
    temp_pdf_paths = []

    for result in results:
        if isinstance(result, tuple):
            document_text, temp_pdf_path = result
            combined_text += document_text
            temp_pdf_paths.append(temp_pdf_path)
        else:
            logging.error(f"Error in processing document: {result}")

    return combined_text, temp_pdf_paths

@error_handler
async def handle_single_document(url, email, passcode, doc_name=None):
    temp_pdf_dir = 'temp_pdfs'
    os.makedirs(temp_pdf_dir, exist_ok=True)
    
    temp_pdf_path = os.path.join(temp_pdf_dir, f'{doc_name}.pdf') if doc_name else os.path.join(temp_pdf_dir, 'temp_docsend.pdf')

    kwargs = generate_pdf_from_docsend_url(url, email, passcode, searchable=True)
    
    with open(temp_pdf_path, 'wb') as f:
        f.write(kwargs['content'])
    
    if os.path.exists(temp_pdf_path):
        file_size = os.path.getsize(temp_pdf_path)
        logging.info(f"File {temp_pdf_path} written successfully with size {file_size} bytes.")
    else:
        logging.error(f"File {temp_pdf_path} was not written successfully.")
    
    extracted_text = extract_text_from_pdf(temp_pdf_path)
    return normalize_text(extracted_text) + "\n", temp_pdf_path  

@error_handler
def extract_document_links(soup):
    data = json.loads(soup.text)
    unescaped_html = html.unescape(data['viewer_html'])
    soup = BeautifulSoup(unescaped_html, 'html.parser')
    container = soup.find('div', class_='bundle-viewer')
    return container.find_all('a', href=True)

def generate_pdf_from_docsend_url(url, email, passcode='', searchable=True):
    credentials = docsend2pdf_credentials()
    kwargs = dict(email=email, passcode=passcode, searchable=searchable, **credentials)
    return docsend2pdf_translate(url, **kwargs)

@error_handler
def docsend2pdf_credentials():
    with requests.Session() as session:
        response = session.get('https://docsend2pdf.com')
        response.raise_for_status()
        cookies = session.cookies.get_dict()
        soup = BeautifulSoup(response.text, 'html.parser')
        csrfmiddlewaretoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        return {'csrfmiddlewaretoken': csrfmiddlewaretoken, 'csrftoken': cookies.get('csrftoken', '')}

@error_handler
def docsend2pdf_translate(url, csrfmiddlewaretoken, csrftoken, email, passcode='', searchable=False):
    with requests.Session() as session:
        session.cookies.set('csrftoken', csrftoken)
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': 'https://docsend2pdf.com/'}
        data = {'csrfmiddlewaretoken': csrfmiddlewaretoken, 'url': url, 'email': email, 'passcode': passcode}
        if searchable:
            data['searchable'] = 'on'
        response = session.post('https://docsend2pdf.com', headers=headers, data=data, allow_redirects=True, timeout=60)
        response.raise_for_status()
        return {'content': response.content, 'headers': {'Content-Type': response.headers['Content-Type'], 'Content-Disposition': response.headers.get('Content-Disposition', f'inline; filename="{url}.pdf"')}}

@error_handler
def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        with ThreadPoolExecutor(max_workers=4) as executor:
            return "".join(executor.map(process_page, doc))
    except Exception as e:
        logging.error(f"Error processing PDF: {file_path} | {e}")
        return ""

def process_page(page):
    page_text = page.get_text()
    return page_text if page_text.strip() else ocr_page(page)

@error_handler
def ocr_page(page):
    page_pix = page.get_pixmap()
    img = Image.frombytes("RGB", [page_pix.width, page_pix.height], page_pix.samples)
    return pytesseract.image_to_string(img)

def normalize_text(text):
    # Replace multiple spaces with a single space
    text = re.sub(r'\s{2,}', ' ', text)
    
    # Remove spaces between letters that are likely part of the same word
    text = re.sub(r'(?<=\w)\s+(?=\w)', '', text)
    
    # Remove newlines followed by spaces or within words
    text = re.sub(r'\n\s+', ' ', text)
    text = re.sub(r'(?<!\n)\n(?!\n)', '', text)
    
    # Fix common OCR issues where characters are split
    text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)  # Join split characters
    text = re.sub(r'(\w)\s+\-', r'\1-', text)  # Join split words before hyphens
    text = re.sub(r'\-\s+(\w)', r'-\1', text)  # Join split words after hyphens
    
    # Handle em-dashes and multiple spaces around them
    text = re.sub(r'\s-\s', '-', text)
    text = re.sub(r'—', '-', text)
    text = re.sub(r'\s—\s', '-', text)

    # Strip leading and trailing whitespace
    return text.strip()

def move_pdfs_to_account_directory(account_name, pdf_paths):
    account_dir = os.path.join('account_pdfs', account_name)
    os.makedirs(account_dir, exist_ok=True)
    
    moved_paths = []
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            new_path = os.path.join(account_dir, os.path.basename(pdf_path))
            shutil.move(pdf_path, new_path)
            moved_paths.append(new_path)
            logging.info(f"Moved {pdf_path} to {new_path}")
        else:
            logging.warning(f"File not found: {pdf_path}")
    
    return moved_paths


def is_valid_docsend_document(session, url):
    if 'docsend.com' not in url or '/view/' not in url:
        return False
    
    try:
        response = session.get(url, allow_redirects=False)
        if response.status_code == 302:  # Check if it's a redirect
            location = response.headers.get('Location', '')
            if 'youtube.com' in location or 'youtu.be' in location:
                logging.info(f"URL {url} redirects to YouTube. Skipping.")
                return False
        return True
    except Exception as e:
        logging.error(f"Error checking URL {url}: {str(e)}")
        return False