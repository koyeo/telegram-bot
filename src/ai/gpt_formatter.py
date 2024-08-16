import openai
import logging
import re
import json

client = openai.OpenAI()

def format_message_with_gpt(message_text, expected_fields=None, mode='format'):
    if mode == 'format':
        function_description = {
            "name": "format_deal",
            "description": "Format a Telegram message into a structured deal flow record",
            "parameters": {
                "type": "object",
                "properties": {
                    "Deal ID": {"type": "string"},
                    "Account Name / PortCo": {"type": "string"},
                    "Record Type ID": {"type": "string"},
                    "Deal Name": {"type": "string"},
                    "Stage": {"type": "string"},
                    "Account Description": {"type": "string"},
                    "Website": {"type": "string"},
                    "Deck": {"type": "string"},
                    "Fundraise Amount($USD)": {"type": "string"},
                    "Equity Valuation/Cap": {"type": "string"},
                    "Token Valuation": {"type": "string"},
                    "CMT Relationship Owner": {"type": "string"},
                    "Sharepoint Link": {"type": "string"},
                    "Round": {"type": "string"}
                },
                "required": ["Account Name / PortCo", "Record Type ID", "Deal Name", "Stage", "Account Description"]
            }
        }
        prompt = f"""
        Format the blurb from this Telegram message into a structured venture dealflow record.
        Use 'Record Type ID': '012Dm0000012ZYDIA2' and 'Stage': 'New' as hardcoded values.
        Leave 'Deal ID', 'CMT Relationship Owner', and 'Sharepoint Link' blank.
        For 'Deal Name', use the format: "<Company/project name> - <round> - <current year>" or "<Company/project name> - <current year>".
        For 'Account Description' please provide information on what the company/project does.
        For 'Account Name / Portco' find the name of the company or project based on the context provided. 
        Format monetary values in $X,XXX,XXX format.
        Message: {message_text}
        """
    elif mode == 'parse':
        function_description = {
            "name": "parse_venture_deal",
            "description": "Parse missing fields for a venture deal record from user's reply",
            "parameters": {
                "type": "object",
                "properties": {field: {"type": "string"} for field in expected_fields},
                "required": expected_fields
            }
        }
        prompt = f"""
        The following fields are missing from a venture deal record. Extract the relevant information from the user's reply:
        Missing Fields: {', '.join(expected_fields)}
        User's Reply: {message_text}
        Fill in the missing fields, leaving as empty string if not found.
        Format monetary values in $X,XXX,XXX format if applicable.
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who extracts and organizes information for venture deals."},
                {"role": "user", "content": prompt}
            ],
            functions=[function_description],
            function_call={"name": function_description["name"]},
            temperature=0.3,
        )

        function_response = response.choices[0].message.function_call.arguments
        return json.loads(function_response)

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON content: {e}")
        logging.error(f"Function Response: {function_response}")
        return {}
    except openai.APIConnectionError as e:
        logging.error("The server could not be reached")
        logging.error(e.__cause__)
    except openai.RateLimitError as e:
        logging.error("A 429 status code was received; we should back off a bit.")
    except openai.APIStatusError as e:
        logging.error("Another non-200-range status code was received")
        logging.error(e.status_code)
        logging.error(e.response)
    except Exception as e:
        logging.error(f"Unexpected error while using GPT: {e}")
        return {}


def generate_title_with_gpt(message_text):
    prompt = (
        "Please provide a short and descriptive title for the following document. Using the name of the company followed by a description of its contents (e.g. deck, whitepaper) will usually be best:\n\n"
        f"{message_text[:1000]}"  # Send only the first 1000 characters to keep it concise
    )

    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=5,
            temperature=0.2,
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


def sanitize_filename(filename):
    """Sanitize a filename to remove/replace unsafe characters."""
    return re.sub(r'[^\w\-_. ]', '_', filename).strip()
    