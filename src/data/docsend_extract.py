import requests
from bs4 import BeautifulSoup
import logging
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from concurrent.futures import ThreadPoolExecutor
import re
import time

import json
import html 

def extract_docsend_content(url, email, passcode=''):
    try:
        logging.info(f"Starting extraction for URL: {url}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',  # Do Not Track Request Header
        })
        
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        if 'input' in response.text and 'authenticity_token' in response.text:
            logging.info("Authentication required. Proceeding with authentication.")
            csrf_token_tag = soup.find('meta', {'name': 'csrf-token'})
            if csrf_token_tag:
                csrf_token = csrf_token_tag['content']
                auth_response = authenticate_docsend(session, url, email, passcode, csrf_token)
                soup = BeautifulSoup(auth_response.text, 'html.parser')
            else:
                logging.error("CSRF token not found.")
                return "CSRF token not found."

        # Check if the URL is a dataroom or a single document
        if '/s/' in url:
            # This is a dataroom
            logging.info("Detected dataroom link.")
            combined_text = handle_dataroom(session, soup, email, passcode)
        else:
            # This is a single document link
            logging.info("Detected single document link.")
            combined_text = handle_single_document(url, email, passcode)
        
        logging.info(f"Combined text extracted from DocSend: {combined_text[:500]}...")  # Log the first 500 characters for debugging
        return combined_text
    except AttributeError as e:
        logging.error(f"Error extracting content from DocSend link: Attribute error - {e}")
        return "Error extracting content from DocSend link."
    except Exception as e:
        logging.error(f"Error extracting content from DocSend link: {e}")
        return "Error extracting content from DocSend link."

def authenticate_docsend(session, url, email, passcode, csrf_token):
    try:
        auth_data = {
            'utf8': '✓',
            '_method': 'patch',
            'authenticity_token': csrf_token,
            'link_auth_form[email]': email,
            'link_auth_form[passcode]': passcode,
            'commit': 'Continue'
        }
        auth_response = session.post(url, data=auth_data)
        auth_response.raise_for_status()
        logging.info(f"Authenticated with email: {email}")
        return auth_response
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        raise


def handle_dataroom(session, soup, email, passcode):
    try:
        raw_html = soup.text
        data = json.loads(raw_html)

        viewer_html = data['viewer_html']
        unescaped_html = html.unescape(viewer_html)

        soup = BeautifulSoup(unescaped_html, 'html.parser')

        container = soup.find('div', class_='bundle-viewer')
        doc_links = container.find_all('a', href=True)

        logging.info(f"Found {len(doc_links)} document links in the dataroom.")

        for idx, link in enumerate(doc_links, start=1):
            if 'href' in link.attrs:
                href = link['href']
                logging.info(f"Document link {idx} href: {href}")
            else:
                logging.warning(f"Skipping document link without href attribute: {link}")

        combined_text = ""
        for link in doc_links:
            if 'href' in link.attrs:
                doc_url = link['href']
                logging.info(f"Processing document: {doc_url}")

                kwargs = generate_pdf_from_docsend_url(doc_url, email, passcode, searchable=True)
                
                temp_pdf_path = 'temp_docsend.pdf'
                with open(temp_pdf_path, 'wb') as f:
                    f.write(kwargs['content'])

                extracted_text = extract_text_from_pdf(temp_pdf_path)

                os.remove(temp_pdf_path)

                combined_text += extracted_text + "\n"
            else:
                logging.warning(f"Skipping document link without href attribute: {link}")

        return combined_text
    except Exception as e:
        logging.error(f"Error handling dataroom: {e}")
        return ""



def handle_single_document(url, email, passcode):
    try:
        kwargs = generate_pdf_from_docsend_url(url, email, passcode, searchable=True)
        
        temp_pdf_path = 'temp_docsend.pdf'
        with open(temp_pdf_path, 'wb') as f:
            f.write(kwargs['content'])

        extracted_text = extract_text_from_pdf(temp_pdf_path)

        os.remove(temp_pdf_path)

        return extracted_text
    except Exception as e:
        logging.error(f"Error handling single document: {e}")
        return ""

def generate_pdf_from_docsend_url(url, email, passcode='', searchable=True):
    logging.info(f"Generating PDF from DocSend URL: {url}")
    credentials = docsend2pdf_credentials()
    kwargs = dict(
        email=email,
        passcode=passcode,
        searchable=searchable,
        **credentials
    )
    return docsend2pdf_translate(url, **kwargs)

def docsend2pdf_credentials():
    with requests.Session() as session:
        start_time = time.time()
        logging.info(f"Fetching docsend2pdf CSRF tokens...")
        response = session.get('https://docsend2pdf.com')
        logging.info(f"Received docsend2pdf CSRF tokens in {time.time() - start_time} seconds.")
        if response.ok:
            cookies = session.cookies.get_dict()
            csrftoken = cookies.get('csrftoken', '')
            soup = BeautifulSoup(response.text, 'html.parser')
            csrfmiddlewaretoken_tag = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrfmiddlewaretoken_tag:
                csrfmiddlewaretoken = csrfmiddlewaretoken_tag['value']
                return {'csrfmiddlewaretoken': csrfmiddlewaretoken, 'csrftoken': csrftoken}
            else:
                logging.error("CSRF middleware token not found.")
                return None
        else:
            response.raise_for_status()

def docsend2pdf_translate(url, csrfmiddlewaretoken, csrftoken, email, passcode='', searchable=False):
    logging.info(f"Translating DocSend URL: {url}")
    with requests.Session() as session:
        session.cookies.set('csrftoken', csrftoken)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://docsend2pdf.com/'
        }
        data = {
            'csrfmiddlewaretoken': csrfmiddlewaretoken,
            'url': url,
            'email': email,
            'passcode': passcode,
        }
        if searchable:
            data['searchable'] = 'on'
        start_time = time.time()
        logging.info(f"Converting {url} on behalf of {email}...")
        response = session.post('https://docsend2pdf.com', headers=headers, data=data, allow_redirects=True, timeout=60)
        if response.ok:
            logging.info(f"Conversion successful, received {response.headers['Content-Length']} bytes in {time.time() - start_time} seconds.")
            kwargs = dict(
                content=response.content,
                headers={
                    'Content-Type': response.headers['Content-Type'],
                    'Content-Disposition': response.headers.get('Content-Disposition', f'inline; filename="{url}.pdf"')
                }
            )
            return kwargs
        else:
            response.raise_for_status()

def extract_text_from_pdf(file_path):
    logging.info(f"Extracting text from PDF: {file_path}")
    text = ""
    doc = fitz.open(file_path)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_page, page) for page in doc]
        for future in futures:
            text += future.result()
    return text

def process_page(page):
    logging.info(f"Processing page with text extraction.")
    page_text = page.get_text()
    if not page_text.strip():
        # If no text is found, use OCR as a fallback
        page_text = ocr_page(page)
    return page_text

def ocr_page(page):
    logging.info(f"Performing OCR on page.")
    try:
        page_pix = page.get_pixmap()
        img = Image.frombytes("RGB", [page_pix.width, page_pix.height], page_pix.samples)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        logging.error(f"OCR processing error: {e}")
        return "Error performing OCR"
