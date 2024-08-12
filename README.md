# Telegram Bot CSV Extractor

This project implements a Telegram bot that receives messages, extracts key details, and saves them to a CSV file.

## Setup (Local)

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix or MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up your Telegram bot and obtain the token
6. Set the environment variables: `export TELEGRAM_BOT_TOKEN=your_token_here`
8. Run the bot: `python main.py`

## Setup (Production)

1. Obtain keys and environment variables from admin
2. SSH into server
3. Clone repository in server
4. Create .env file and set environment variables
5. Run the bot: `docker compose up --build -d` 

## Usage

Once the bot is running, it will automatically process incoming messages and save the extracted details to `data/telegram_messages.csv`.
