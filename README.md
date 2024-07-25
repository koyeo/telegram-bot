# Telegram Bot CSV Extractor

This project implements a Telegram bot that receives messages, extracts key details, and saves them to a CSV file.

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix or MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up your Telegram bot and obtain the token
6. Set the environment variable: `export TELEGRAM_BOT_TOKEN=your_token_here`
7. Update the `config/config.yaml` file with your webhook URL
8. Run the bot: `python main.py`

## Usage

Once the bot is running, it will automatically process incoming messages and save the extracted details to `data/telegram_messages.csv`.

## Testing

To run tests: `python -m unittest discover tests`