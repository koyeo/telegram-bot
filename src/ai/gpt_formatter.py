import os
import openai
import logging
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def format_message_with_gpt(message_text, message_date):
    prompt = f"""
    Format the following Telegram message into a structured format with these fields:
    - Deal ID: Name of the project or company that the message is about
    - Description: A brief summary of the message content
    - Website: Website link if included
    - Deck: Link to the pitch deck if included
    - Fundraise Amount($USD): The amount in $X,XXX,XXX format if it is included; otherwise leave blank
    - Valuation: The project valuation in $X,XXX,XXX format if it is included; otherwise leave blank
    - Date: {message_date}

    Message: {message_text}

    Formatted Output:
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        logging.info(f"OpenAI response: {response}")
        return response['choices'][0]['message']['content'].strip()
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {str(e)}")
        return None
