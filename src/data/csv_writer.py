import csv
import os
import logging

async def save_to_csv(details):
    if not os.path.exists('data'):
        os.makedirs('data')
    
    filepath = os.path.join('data', 'dealflow.csv')
    file_exists = os.path.isfile(filepath)

    logging.info(f"Saving details to CSV: {details}")

    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Deal ID', 'Description', 'Website', 'Deck', 'Fundraise Amount($USD)', 'Valuation', 'Date', 'CMT Owner']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(details)
        logging.info("Details saved to CSV successfully")
    except Exception as e:
        logging.error(f"Failed to save details to CSV: {e}")