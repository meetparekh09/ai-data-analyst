import os
import sys
import dotenv
import xmltodict
import logging
import pandas as pd
from openai import OpenAI

from constants import SYSTEM_PROMPT_DATA_ACQUISITION, SAMPLE_USER_MESSAGE
from util import get_logger
dotenv.load_dotenv(dotenv_path="./openai.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_COMPLETION_MODEL = os.getenv("OPENAI_COMPLETION_MODEL")

logger = get_logger(__name__)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

path = "data/netflix_titles.csv"

def get_data(path, logger):
    ldict = {}    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_DATA_ACQUISITION},
        {"role": "user", "content": SAMPLE_USER_MESSAGE.format(path_name=path, logger_name=logger)},
    ]
    retry = 0
    while retry < 3:
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=messages,
        )
        parsed_response = xmltodict.parse(response.choices[0].message.content)
        logger.info(parsed_response)

        try:
            output = parsed_response["output"]
            if output["@type"] != "code":
                retry += 1
                logger.info(f"Retrying as output is not code: {retry} of 3")
                continue
            
            if output["@language"] != "python":
                retry += 1
                logger.info(f"Retrying as output is not python: {retry} of 3")
                continue
            
            code = output["#text"].replace("\n    ", "\n")
            logger.info(f"Executing code: {code}")
            exec(code, globals(), ldict)
            break
        except Exception as e:
            retry += 1
            logger.info(f"Error: {e}")
            logger.info(f"Retry {retry} of 3")
    
    if "df" not in ldict:
        logger.error("Failed to get data")
        return None
    
    return ldict["df"]


if __name__ == "__main__":
    df = get_data(path, logger)
    if df is None:
        logger.error("Failed to get data")
        sys.exit(1)
    
    logger.info(df)
