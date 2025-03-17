import io
import traceback
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from clients import get_openai_client
from prompts import (
    DESCRIPTIVE_STATISTICS_PROMPT_MD,
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

def descriptive_statistics(df, data_cleaning_report, logger):
    client = get_openai_client()
    ldict = locals()
    descriptive_statistics_report = None
    descriptive_statistics_messages = [
        {
            "role": "system",
            "content": DESCRIPTIVE_STATISTICS_PROMPT_MD.format(
                df_name="df",
                data_cleaning_report=data_cleaning_report,
                df_columns_output=df.columns,
                df_dtypes_output=df.dtypes,
                df_describe_output=df.describe(),
            )
        }
    ]
    retry = 0
    while retry < 3:
        try:
            logger.info("Planning for Descriptive Statistics")
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=descriptive_statistics_messages,
                temperature=OPENAI_TEMPERATURE,
                stop=["## Report from Descriptive Statistics", "### User Feedback"],
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
            descriptive_statistics_messages.append({"role": "assistant", "content": output})
            user_feedback_count = 0
            while contains_code == "False" and user_feedback_count < 3:
                logger.info(output)
                user_feedback = input("Enter your feedback: ")
                descriptive_statistics_messages.append({"role": "user", "content": USER_FEEDBACK_PROMPT_MD.format(user_feedback=user_feedback)})
                response = client.chat.completions.create(
                    model=OPENAI_COMPLETION_MODEL,
                    messages=descriptive_statistics_messages,
                    temperature=OPENAI_TEMPERATURE,
                    stop=["## Report from Descriptive Statistics"]
                )
                output = response.choices[0].message.content
                descriptive_statistics_messages.append({"role": "assistant", "content": output})
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
            
            
            logger.info("Extracting code from Descriptive Statistics Plan")
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
            descriptive_statistics_code = response.choices[0].message.content.replace("```python", "").replace("```", "")
        except Exception as e:
            retry += 1
            logger.error(f"Error: {e}")
            logger.info("Failed to run descriptive statistics, and extracting code from descriptive statistics. Retrying...")
            logger.info(f"Retry {retry} of 3")
            continue
        
        try:
            logger.info("Running descriptive statistics code")
            exec(descriptive_statistics_code, globals(), ldict)
        except Exception as e:
            string_buffer = io.StringIO()
            traceback.print_exc(file=string_buffer)
            error_message = string_buffer.getvalue()
            error_messages_prompts = [
                {"role": "system", "content": CODE_ERROR_SYSTEM_PROMPT_MD},
                {"role": "user", "content": CODE_ERROR_PROMPT_USER_MESSAGE_MD.format(
                    reasoning_of_the_code=descriptive_statistics_messages[-1]["content"],
                    code=descriptive_statistics_code,
                    error=error_message,
                )},
            ]
            response = client.chat.completions.create(
                model=OPENAI_COMPLETION_MODEL,
                messages=error_messages_prompts,
                temperature=OPENAI_TEMPERATURE,
            )
            error_output = response.choices[0].message.content
            descriptive_statistics_messages.append({"role": "user", "content": error_output})
            retry += 1
            logger.error(f"Error: {e}")
            logger.info("Failed to run descriptive statistics code. Retrying...")
            logger.info(f"Retry {retry} of 3")
            continue
        
        descriptive_statistics_messages.append({"role": "user", "content": "Code ran successfully. Can you generate the report?\n## Report from Descriptive Statistics"})
        response = client.chat.completions.create(
            model=OPENAI_COMPLETION_MODEL,
            messages=descriptive_statistics_messages,
            temperature=OPENAI_TEMPERATURE,
        )
        descriptive_statistics_report = response.choices[0].message.content
        break
    
    return descriptive_statistics_report