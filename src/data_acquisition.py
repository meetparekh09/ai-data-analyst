import pandas as pd

from util import print_logprobs
from prompts import (
    SYSTEM_PROMPT_DATA_ACQUISITION_MD,
    SAMPLE_USER_MESSAGE_MD,
)
from constants import (
    OPENAI_COMPLETION_MODEL,
    OPENAI_TEMPERATURE,
)
from clients import get_openai_client



def get_data(path, file_type, logger, verbose=False, n=2):
    user_prompt = SAMPLE_USER_MESSAGE_MD.format(path_name=path, file_type=file_type, logger_name=logger)
    client = get_openai_client()
    ldict = locals()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_DATA_ACQUISITION_MD},
        {"role": "user", "content": user_prompt},
    ]
    retry = 0
    while retry < 3:
        logger.info("Getting data")
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=messages,
            logprobs=verbose,
            n=n if verbose else 1,
        )
        if verbose:
            logger.info(f"Printing top {n} logprobs:")
            print_logprobs(response.choices[0].logprobs.content, logger)
            print_logprobs(response.choices[1].logprobs.content, logger)

        try:
            output = response.choices[0].message.content.replace("```python", "").replace("```", "")
            code = output.replace("\n    ", "\n")
            if verbose:
                logger.info(f"\n\nExecuting code:\n{code}")
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

def _get_data_static(path="data/online_retail_2.xlsx", logger=None):
    df = pd.read_excel(path)
    return df