import csv
import os

def save_to_csv(details):
    filepath = os.path.join('data', 'telegram_messages.csv')
    file_exists = os.path.isfile(filepath)
    
    with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Deal ID', 'Description', 'Website', 'Deck', 'Fundraise Amount($USD)', 'Valuation', 'Date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(details)