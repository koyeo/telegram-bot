import os
import logging

COUNTER_FILE_PATH = "deal_counter.txt"

def load_deal_counter():
    if os.path.exists(COUNTER_FILE_PATH):
        with open(COUNTER_FILE_PATH, "r") as file:
            try:
                return int(file.read().strip())
            except ValueError:
                logging.warning("Counter file is corrupted. Resetting counter to 1.")
                return 1
    else:
        return 1

def save_deal_counter(counter):
    with open(COUNTER_FILE_PATH, "w") as file:
        file.write(str(counter))

def get_next_deal_id():
    global deal_counter
    deal_counter = load_deal_counter()  # Load the counter from the file
    deal_id = f"Deal_{deal_counter:04d}"
    deal_counter += 1
    save_deal_counter(deal_counter)  # Save the updated counter back to the file
    return deal_id
