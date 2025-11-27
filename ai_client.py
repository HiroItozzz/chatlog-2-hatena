import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY', "").strip()
DEBUG = os.getenv('DEBUG', 'False').lower() in ("true", "1", "t")

CUSTOM_PROMPT = "以下の一日の対話型AIとのやり取りの内容をプログラミングの学習記録としてブログに上げようと思います。日本語で要約し、2000字以内で文章化してください。:" 

TEXT = ""

def get_summary_from_gemini(text: str, api_key: str, custom_prompt: str = CUSTOM_PROMPT) -> str:

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client(API_KEY)


    # Turn off thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=0)
    # Turn on dynamic thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=-1)
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=f"",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
            )
        )
    print(response.text)
    return response.text
