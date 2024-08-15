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
    return process_documents(doc_links, email, passcode)

@error_handler
def handle_single_document(url, email, passcode):
    kwargs = generate_pdf_from_docsend_url(url, email, passcode, searchable=True)
    with open('temp_docsend.pdf', 'wb') as f:
        f.write(kwargs['content'])
    extracted_text = extract_text_from_pdf('temp_docsend.pdf')
    os.remove('temp_docsend.pdf')
    return normalize_text(extracted_text)

@error_handler
def extract_document_links(soup):
    data = json.loads(soup.text)
    unescaped_html = html.unescape(data['viewer_html'])
    soup = BeautifulSoup(unescaped_html, 'html.parser')
    container = soup.find('div', class_='bundle-viewer')
    return container.find_all('a', href=True)

@error_handler
def process_documents(doc_links, email, passcode):
    return "".join([process_single_document(link['href'], email, passcode) for link in doc_links if 'href' in link.attrs])

    # """
    # Processes each document link, extracting and normalizing text.
    # """
    # combined_text = ""

    # # Filter and process each valid document link
    # for link in doc_links:
    #     if 'href' in link.attrs:
    #         # Process each document and add the text to combined_text
    #         document_text = process_single_document(link, email, passcode)
    #         combined_text += document_text

    # return combined_text

@error_handler
def process_single_document(doc_url, email, passcode):
    pdf_content = download_pdf(doc_url, email, passcode)
    extracted_text = extract_text_from_pdf(pdf_content)
    logging.info(f"EXTRACTED TEXT: {extracted_text}")
    return normalize_text(extracted_text) + "\n"

@error_handler
def download_pdf(doc_url, email, passcode):
    kwargs = generate_pdf_from_docsend_url(doc_url, email, passcode, searchable=True)
    temp_pdf_path = f'temp_docsend_{os.path.basename(doc_url)}.pdf'
    with open(temp_pdf_path, 'wb') as f:
        f.write(kwargs['content'])
    return temp_pdf_path

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
    # Split lowercase words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    
    # Split words after punctuation
    text = re.sub(r'([.,!?:;-])([a-zA-Z])', r'\1 \2', text)
    
    # Split lowercase words (this is the key addition)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([a-z]{2,})([A-Z])', r'\1 \2', text)
    
    # Handle specific cases
    text = text.replace('Esports', 'E-sports')
    text = text.replace('Berachain', 'Bera chain')
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()