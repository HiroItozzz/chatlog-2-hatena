import os
from pathlib import Path
import time
from dotenv import load_dotenv
import yaml
from google import genai
from google.genai import types



load_dotenv()
config_path = Path('config.yaml')
config = yaml.safe_load(config_path.read_text(encoding='utf-8'))

DEBUG = config['other']['debug'].lower() in ("true", "1", "t")


API_KEY = os.getenv('GEMINI_API_KEY', "").strip()

PROMPT = config['ai']['prompt']
MODEL = config['ai']['model']
LEVEL = config['ai']['thoughts_level']


TEXT = ""

def summary_from_gemini(text: str, api_key: str,  model: str = "gemini-2.5-flash", thoughts_level: int = 0, prompt: str = "please summarize the following conversation for a blog article. Keep it under 200 words: ") -> list[str, int, int]:

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client(api_key=API_KEY)

    # Turn off thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=0)
    # Turn on dynamic thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=-1)
    
    max_retries = 3
    for i in range(max_retries):        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=f"{prompt}\n\n{text}",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=thoughts_level) # disables dynamic thinking for default
                    )
                )
            break
        except Exception as e:
            if '503' in str(e) and i < max_retries - 1:
                print(f"Server seems to be busy. Retry {5 * (i+1)} seconds later.")
                time.sleep(5 * (i+1))  # 5秒、10秒、15秒と待つ
            else:
                raise
    

    input_token = response.usage_metadata.thoughts_token_count
    output_token = response.usage_metadata.candidates_token_count
    message = (
        "static thinking" if thoughts_level == 0 
        else "dynamic thinking" if thoughts_level == -1 
        else f"thoughts limit: {thoughts_level}"
    )

    if DEBUG:
        print(f"Got your summary from AI: {response.text[:100]}")
        print(f"Input tokens: {input_token}, Thoughts level: {message} \nOutput tokens:, {output_token}")

    return response.text, input_token, output_token
