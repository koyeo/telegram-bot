import requests
from bs4 import BeautifulSoup
import logging
import os
import fitz
from PIL import Image
import pytesseract
from concurrent.futures import ThreadPoolExecutor
import re
import json
import html
from functools import wraps

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
def extract_docsend_content(url, email, passcode=''):
    logging.info(f"Starting extraction for URL: {url}")
    session = create_session()
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    if 'input' in response.text and 'authenticity_token' in response.text:
        soup = authenticate(session, url, email, passcode, soup)

    if '/s/' in url:
        return handle_dataroom(session, soup, email, passcode)
    else:
        return handle_single_document(url, email, passcode)

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

@error_handler
def handle_dataroom(session, soup, email, passcode):
    doc_links = extract_document_links(soup)
    logging.info(f"Found {len(doc_links)} document links in the dataroom.")
    combined_text = ""

    for link in doc_links:
        if 'href' in link.attrs:
            doc_url = link['href']
            logging.info(f"Processing document: {doc_url}")

            doc_name_tag = link.find('div', class_='bundle-document_name')
            doc_name = doc_name_tag.text.strip() if doc_name_tag else "unknown_document"
            safe_doc_name = re.sub(r'[^\w\-_\.]', '_', doc_name).replace(' ', '_')
            logging.info(f"Document name extracted: {safe_doc_name}")
            document_text = handle_single_document(doc_url, email, passcode, safe_doc_name)
            logging.info(f"EXTRACTED TEXT: {document_text[:1000]}...")
            combined_text += document_text

    return combined_text

@error_handler
def handle_single_document(url, email, passcode, doc_name=None):
    temp_pdf_path = f'{doc_name}.pdf' if doc_name else 'temp_docsend.pdf'
    kwargs = generate_pdf_from_docsend_url(url, email, passcode, searchable=True)
    with open(temp_pdf_path, 'wb') as f:
        f.write(kwargs['content'])
    extracted_text = extract_text_from_pdf(temp_pdf_path)
    os.remove(temp_pdf_path)
    return normalize_text(extracted_text) + "\n"

@error_handler
def extract_document_links(soup):
    data = json.loads(soup.text)
    unescaped_html = html.unescape(data['viewer_html'])
    soup = BeautifulSoup(unescaped_html, 'html.parser')
    container = soup.find('div', class_='bundle-viewer')
    return container.find_all('a', href=True)

@error_handler
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
    doc = fitz.open(file_path)
    with ThreadPoolExecutor(max_workers=4) as executor:
        return "".join(executor.map(process_page, doc))

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