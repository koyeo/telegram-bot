import csv
import os
import logging

async def save_to_csv(details):
    if not os.path.exists('data'):
        os.makedirs('data')
    
    filepath = os.path.join('data', 'dealflow.csv')
    temp_filepath = os.path.join('data', 'dealflow_temp.csv')  # Temporary file for updates

    logging.info(f"Saving details to CSV: {details}")

    try:
        deal_id = details.get('Deal ID')
        updated = False

        # Read the existing CSV data and write to a temporary file
        with open(filepath, 'r', encoding='utf-8') as csvfile, open(temp_filepath, 'w', newline='', encoding='utf-8') as temp_file:
            reader = csv.DictReader(csvfile)
            writer = csv.DictWriter(temp_file, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                if row['Deal ID'] == deal_id:
                    row.update(details)
                    updated = True
                writer.writerow(row)

        if updated:
            os.remove(filepath)
            os.rename(temp_filepath, filepath)
            logging.info(f"Deal details with ID '{deal_id}' updated successfully.")
        else:
            with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Deal ID', 'Created Date', 'Account Name / PortCo', 'Record Type ID', 'Deal Name', 'Stage', 'Account Description', 'Website', 'Deck', 'Fundraise Amount($USD)', 'Equity Valuation/Cap', 'Token Valuation', 'CMT Relationship Owner', 'Sharepoint Link', 'Round', 'Deal Source', 'File Name']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(details)
            logging.info(f"New deal details added to CSV.")

    except Exception as e:
        logging.error(f"Failed to save details to CSV: {e}")
