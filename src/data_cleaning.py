import io
import traceback
import pandas as pd

from clients import get_openai_client
from prompts import (
    DATA_CLEANING_PROMPT_MD,
    CODE_EXTRACTOR_SYSTEM_PROMPT_MD,
    CODE_EXTRACTOR_USER_MESSAGE_MD,
    CODE_ERROR_SYSTEM_PROMPT_MD,
    CODE_ERROR_PROMPT_USER_MESSAGE_MD,
    USER_FEEDBACK_PROMPT_MD,
    CONTAINS_CODE_PROMPT_MD,
    CONTAINS_CODE_USER_MESSAGE_MD,
)
from constants import (
    OPENAI_COMPLETION_MODEL,
    OPENAI_TEMPERATURE,
)

def data_cleaning(df, preliminary_results, preliminary_description, logger):
    client = get_openai_client()
    ldict = locals()
    data_cleaning_report = None
    data_cleaning_messages = [
        {
            "role": "system",
            "content": DATA_CLEANING_PROMPT_MD.format(
                df_name="df",
                preliminary_results=preliminary_results,
                preliminary_analysis_report=preliminary_description
            )
        }
    ]
    retry = 0
    while retry < 3:
        try:
            logger.info("Cleaning data")
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=data_cleaning_messages,
                temperature=OPENAI_TEMPERATURE,
                stop=["## Report from Data Cleaning", "### User Feedback"],
            )
            output = response.choices[0].message.content
            contains_code_response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=[
                    {"role": "system", "content": CONTAINS_CODE_PROMPT_MD}, 
                    {"role": "user", "content": CONTAINS_CODE_USER_MESSAGE_MD.format(input_text=output)}
                    ],
                temperature=OPENAI_TEMPERATURE,
            )
            contains_code = contains_code_response.choices[0].message.content
            data_cleaning_messages.append({"role": "assistant", "content": output})
            user_feedback_count = 0
            while contains_code == "False" and user_feedback_count < 3:
                logger.info(output)
                user_feedback = input("Enter your feedback: ")
                data_cleaning_messages.append({"role": "user", "content": USER_FEEDBACK_PROMPT_MD.format(user_feedback=user_feedback)})
                response = client.chat.completions.create(
                    model=OPENAI_COMPLETION_MODEL,
                    messages=data_cleaning_messages,
                    temperature=OPENAI_TEMPERATURE,
                    stop=["## Report from Data Cleaning"]
                )
                output = response.choices[0].message.content
                data_cleaning_messages.append({"role": "assistant", "content": output})
                user_feedback_count += 1
                contains_code_response = client.chat.completions.create(
                    model=OPENAI_COMPLETION_MODEL,
                    messages=[
                        {"role": "system", "content": CONTAINS_CODE_PROMPT_MD}, 
                        {"role": "user", "content": CONTAINS_CODE_USER_MESSAGE_MD.format(input_text=output)}
                        ],
                    temperature=OPENAI_TEMPERATURE,
                )
                contains_code = contains_code_response.choices[0].message.content
            
            
            logger.info("Extracting code from Cleaning Plan")
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
            cleaning_code = response.choices[0].message.content.replace("```python", "").replace("```", "")
        except Exception as e:
            retry += 1
            logger.error(f"Error: {e}")
            logger.info("Failed to run data cleaning, and extracting code from data cleaning. Retrying...")
            logger.info(f"Retry {retry} of 3")
            continue
        
        try:
            logger.info("Running cleaning code")
            exec(cleaning_code, globals(), ldict)
        except Exception as e:
            string_buffer = io.StringIO()
            traceback.print_exc(file=string_buffer)
            error_message = string_buffer.getvalue()
            error_messages_prompts = [
                {"role": "system", "content": CODE_ERROR_SYSTEM_PROMPT_MD},
                {"role": "user", "content": CODE_ERROR_PROMPT_USER_MESSAGE_MD.format(
                    reasoning_of_the_code=data_cleaning_messages[-1]["content"],
                    code=cleaning_code,
                    error=error_message,
                )},
            ]
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=error_messages_prompts,
                temperature=OPENAI_TEMPERATURE,
            )
            error_output = response.choices[0].message.content
            data_cleaning_messages.append({"role": "user", "content": error_output})
            retry += 1
            logger.error(f"Error: {e}")
            logger.info("Failed to run cleaning code. Retrying...")
            logger.info(f"Retry {retry} of 3")
            continue
        
        data_cleaning_messages.append({"role": "user", "content": "Code ran successfully. Can you generate the report?\n## Report from Data Cleaning"})
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=data_cleaning_messages,
            temperature=OPENAI_TEMPERATURE,
        )
        data_cleaning_report = response.choices[0].message.content
        break
    
    return data_cleaning_report