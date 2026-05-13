import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

load_dotenv()

# Synchronous client for existing code
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Asynchronous client for parallel processing
async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))