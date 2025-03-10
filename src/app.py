import os
import sys
import dotenv
import xmltodict
import logging
import pandas as pd
from openai import OpenAI
from pathlib import Path

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

path = "data/online_retail_2.xlsx"

def get_data(path, logger, user_prompt):
    ldict = {}    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_DATA_ACQUISITION},
        {"role": "user", "content": user_prompt},
    ]
    import pdb; pdb.set_trace()
    retry = 0
    while retry < 3:
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=messages,
        )
        parsed_response = xmltodict.parse(response.choices[0].message.content.replace("```python", "").replace("```", ""))
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
    file_type = Path(path).suffix.replace(".", "")
    user_prompt = SAMPLE_USER_MESSAGE.format(path_name=path, file_type=file_type, logger_name=logger)
    df = get_data(path, logger, user_prompt)
    if df is None:
        logger.error("Failed to get data")
        sys.exit(1)
    
    logger.info(df)
