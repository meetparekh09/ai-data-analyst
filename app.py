import os
import dotenv
from openai import OpenAI
from constants import SYSTEM_PROMPT_DATA_ACQUISITION, SAMPLE_USER_MESSAGE

dotenv.load_dotenv(dotenv_path="./openai.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_COMPLETION_MODEL = os.getenv("OPENAI_COMPLETION_MODEL")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

response = client.chat.completions.create(
    model=OPENAI_COMPLETION_MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT_DATA_ACQUISITION},
        {"role": "user", "content": SAMPLE_USER_MESSAGE},
    ],
)

print(response.choices[0].message.content)