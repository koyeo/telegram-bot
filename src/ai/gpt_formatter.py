import os
import openai
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

    response = openai.Completion.create(
        engine="gpt-4o-mini	",
        prompt=prompt,
        max_tokens=2000,
        n=1,
        stop=None,
        temperature=0.5,
    )

    return response.choices[0].text.strip()