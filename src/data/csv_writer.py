import csv
import os
from config import CSV_FIELDNAMES
import logging

async def save_to_csv(content_dict):
    logging.info(f"Saving CSV entry with content_dict: {content_dict}")
    filepath = os.path.join('data', 'dealflow.csv')

    # If the file does not exist, create it with the header
    if not os.path.exists(filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()

    # Read the current CSV file into memory to update or append
    updated = False
    temp_file = os.path.join('data', 'dealflow_temp.csv')
    with open(filepath, 'r', encoding='utf-8') as infile, open(temp_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()

        for row in reader:
            if row['Deal ID'] == content_dict['Deal ID']:
                row.update(content_dict)
                updated = True
            writer.writerow(row)

        if not updated:
            writer.writerow(content_dict)

    os.remove(filepath)
    os.rename(temp_file, filepath)
