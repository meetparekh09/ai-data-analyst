from openai import OpenAI

from constants import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

OPENAI_CLIENT = None

def get_openai_client():
    global OPENAI_CLIENT
    if OPENAI_CLIENT is None:
        OPENAI_CLIENT = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
    return OPENAI_CLIENT