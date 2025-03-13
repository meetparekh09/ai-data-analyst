import os
import sys
import dotenv
import xmltodict
import logging
import traceback
import io
import pandas as pd
from openai import OpenAI
from pathlib import Path

from prompts import (
    SYSTEM_PROMPT_DATA_ACQUISITION_MD, 
    SAMPLE_USER_MESSAGE_MD, 
    PRELIMINARY_ANALYSIS_PROMPT_MD, 
    CODE_EXTRACTOR_SYSTEM_PROMPT_MD,
    CODE_EXTRACTOR_USER_MESSAGE_MD,
    OUTPUT_FROM_PRELIMINARY_ANALYSIS_MD,
    CODE_ERROR_SYSTEM_PROMPT_MD,
    CODE_ERROR_PROMPT_USER_MESSAGE_MD
)
from util import get_logger, print_logprobs
dotenv.load_dotenv(dotenv_path="./openai.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_COMPLETION_MODEL = os.getenv("OPENAI_COMPLETION_MODEL")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))

logger = get_logger(__name__)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

path = "data/online_retail_II.csv"

def get_data(path, logger, user_prompt, verbose=False, n=2):
    ldict = {}    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_DATA_ACQUISITION_MD},
        {"role": "user", "content": user_prompt},
    ]
    retry = 0
    while retry < 3:
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

def _get_data_static(path, logger):
    df = pd.read_excel(path)
    return df

def preliminary_analysis(df, logger):
    ldict = {}
    preliminary_analysis_messages = [
        {
            "role": "system",
            "content": PRELIMINARY_ANALYSIS_PROMPT_MD.format(
                df_name="df",
                df_shape_output=df.shape,
                df_columns_output=df.columns,
                df_dtypes_output=df.dtypes,
                df_describe_output=df.describe(),
            ),
        },
    ]
    retry = 0
    preliminary_results = None
    preliminary_description = None

    while retry < 3:
        try:
            logger.info(f"Performing preliminary analysis")
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=preliminary_analysis_messages,
                temperature=OPENAI_TEMPERATURE,
                stop=["## Output from the Preliminary Analysis"],
            )

            output = response.choices[0].message.content
            preliminary_analysis_messages.append({"role": "assistant", "content": output})
            logger.info("Extracting code from preliminary analysis")
            coding_extractor_messages = [
                {
                    "role": "system",
                    "content": CODE_EXTRACTOR_SYSTEM_PROMPT_MD,
                },
                {
                    "role": "user",
                    "content": CODE_EXTRACTOR_USER_MESSAGE_MD.format(input_text=output),
                },
            ]
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=coding_extractor_messages,
                temperature=OPENAI_TEMPERATURE,
                stop=["## Input Text"],
            )
            analysis_code = response.choices[0].message.content.replace("```python", "").replace("```", "")
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Failed to run preliminary analysis, and extracting code from preliminary analysis. Retrying...")
            logger.info(f"Retry {retry} of 3")
            continue

        try:
            logger.info("Running analysis code.")
            exec(analysis_code, globals(), ldict)
            preliminary_results = ldict["preliminary_results"]
        except Exception as e:
            logger.info("Failed to run analysis code. Detecting error and fixing it...")
            string_buffer = io.StringIO()
            traceback.print_exc(file=string_buffer)
            error_message = string_buffer.getvalue()
            error_messages_prompts = [
                {"role": "system", "content": CODE_ERROR_SYSTEM_PROMPT_MD},
                {"role": "user", "content": CODE_ERROR_PROMPT_USER_MESSAGE_MD.format(
                    reasoning_of_the_code=preliminary_analysis_messages[-1]["content"],
                    code=analysis_code,
                    error=error_message,
                )},
            ]
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=error_messages_prompts,
                temperature=OPENAI_TEMPERATURE,
            )
            error_output = response.choices[0].message.content
            preliminary_analysis_messages.append({"role": "user", "content": error_output})
            retry += 1
            logger.info(f"Error: {e}")
            logger.info(f"Retry {retry} of 3")
            continue
        
        logger.debug(f"Preliminary results:\n{preliminary_results}")
        logger.info("Generating description of the analysis for data cleaning, visualization, and descriptive statistics")
        preliminary_analysis_messages.append({"role": "assistant", "content": OUTPUT_FROM_PRELIMINARY_ANALYSIS_MD.format(preliminary_results=preliminary_results)})
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=preliminary_analysis_messages,
            temperature=OPENAI_TEMPERATURE,
        )
        preliminary_description = response.choices[0].message.content
        logger.debug(f"Preliminary description:\n{preliminary_description}")
        break

    return preliminary_results, preliminary_description
    

if __name__ == "__main__":
    file_type = Path(path).suffix.replace(".", "")
    user_prompt = SAMPLE_USER_MESSAGE_MD.format(path_name=path, file_type=file_type, logger_name=logger)

    logger.info("Getting data")
    df = get_data(path, logger, user_prompt)
    # df = _get_data_static(path, logger)
    if df is None:
        logger.error("Failed to get data")
        sys.exit(1)
    
    logger.info("Running preliminary analysis")
    preliminary_results, preliminary_description = preliminary_analysis(df, logger)
    logger.info(f"Preliminary results:\n{preliminary_results}")
    logger.info(f"Preliminary description:\n{preliminary_description}")
