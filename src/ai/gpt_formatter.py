import os
import openai
import logging

client = openai.OpenAI()

def format_message_with_gpt(message_text):
    prompt = f"""
    Format the blurb from this Telegram message into a structured format with these fields:
    - Deal ID: Leave blank
    - Account Name / PortCo: Name of the project or company that the message is about
    - Record Type ID: Should always be hardcoded as "012Dm0000012ZYDIA2"
    - Deal Name: Should be in format <Company/project name> - <round i.e., Seed, Pre-Seed, Series A (leave blank if not avail)> - <current year>
    - Stage: Should always be hardcoded as "New"
    - Account Description: A brief summary of the message content
    - Website: Website link if included
    - Deck: Link to the pitch deck if included
    - Fundraise Amount($USD): The amount in $X,XXX,XXX format if it is included; otherwise leave blank
    - Equity Valuation/Cap: The project equity valuation in $X,XXX,XXX format if it is included; otherwise leave blank
    - Token Valuation: The project token valuation in $X,XXX,XXX format if it is included; otherwise leave blank
    - CMT Relationship Owner: CMT investor who sent the deal (program will find this automatically)
    - Sharepoint Link: Leave blank
    - Round: i.e., Seed, Pre-Seed, Series A, etc.. if included; otherwise leave blank

    Message: {message_text}

    Formatted Output:
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who will sort through all of the venture deals that are sent to me. You will sift through the blurbs that are sent and identify key information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        logging.info(f"OpenAI response: {response}")
        return response.choices[0].message.content
    except openai.APIConnectionError as e:
        logging.error("The server could not be reached")
        logging.error(e.__cause__)  # an underlying Exception, likely raised within httpx.
    except openai.RateLimitError as e:
        logging.error("A 429 status code was received; we should back off a bit.")
    except openai.APIStatusError as e:
        logging.error("Another non-200-range status code was received")
        logging.error(e.status_code)
        logging.error(e.response)