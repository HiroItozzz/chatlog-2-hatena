import os
from pathlib import Path
import time
from dotenv import load_dotenv
import yaml
from google import genai
from google.genai import types



load_dotenv(override=True)
config_path = Path('config.yaml')
config = yaml.safe_load(config_path.read_text(encoding='utf-8'))

DEBUG = config['other']['debug'].lower() in ("true", "1", "t")


API_KEY = os.getenv('GEMINI_API_KEY', "").strip()

PROMPT = config['ai']['prompt']
MODEL = config['ai']['model']
LEVEL = config['ai']['thoughts_level']

TEXT = ""


class Gemini_fee:
    def __init__(self):
        self.fees = {
            'gemini-2.5-flash': {
                'input': 0.03,   # $per 1M tokens
                'output': 2.5
            },
            'gemini-2.5-pro': {
                'under 0.2M': {
                    'input': 1.25,
                    'output': 10.00
                },
                'over 0.2M': {
                    'input': 2.5,
                    'output': 15
                    }
            }
        }
    
    def calculate(self, model: str, token_type: str, tokens: int) -> float:
        if model == 'gemini-2.5-pro':
            base_fees = self.fees['gemini-2.5-pro']
            if tokens <= 200000:
                return tokens * base_fees['under 0.2M'][token_type] / 1000000
            else:
                return tokens * base_fees['over 0.2M'][token_type] / 1000000
        else:
            return tokens * self.fees[model][token_type] / 1000000



def summary_from_gemini(conversation: str, api_key: str,  model: str = "gemini-2.5-pro", thoughts_level: int = 0, custom_prompt: str = "please summarize the following conversation for a blog article. Keep it under 200 words: ") -> list[str, int, int]:

    if DEBUG:
        print(f"Gemini using API_KEY now: '...{api_key[-5:]}'")
    
    # The client gets the API key from the environment variable `GEMINI_API_KEY` automatically.
    client = genai.Client(api_key=api_key)

    # Turn off thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=0)
    # Turn on dynamic thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=-1)
    
    max_retries = 3
    for i in range(max_retries):        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=f"{custom_prompt}\n\n{conversation}",
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
    

    message = (
        "static thinking" if thoughts_level == 0 
        else "dynamic thinking" if thoughts_level == -1 
        else f"thoughts limit: {thoughts_level}"
    )

    input_tokens = response.usage_metadata.prompt_token_count
    thoughts_tokens= response.usage_metadata.thoughts_token_count
    output_tokens = response.usage_metadata.candidates_token_count

    if DEBUG:
        total_output_tokens = thoughts_tokens + output_tokens
        input_fee = Gemini_fee().calculate(model,token_type="input", tokens=input_tokens)
        thoughts_fee = Gemini_fee().calculate(model, "output", thoughts_tokens)
        output_fee = Gemini_fee().calculate(model, "output", output_tokens)
        total_output_fee = thoughts_fee + output_fee        

        print(f"Got your summary from AI: {response.text[:100]}")
        print(f"Input tokens: {input_tokens},fee: {input_fee}\n \
              Thoughts tokens: {thoughts_tokens}, fee: {thoughts_fee}\n \
                Output_tokens: {output_tokens}, fee: {output_fee}\n \
              Total ouput tokens: {total_output_tokens}, fee: {total_output_fee}\n \
              Total fee: {input_fee + total_output_fee}\n \
                Thoughts level: {message} ")

    return response.text, input_tokens, thoughts_tokens, output_tokens
