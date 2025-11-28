import os
from pathlib import Path
import json, csv
import time
from datetime import datetime, timedelta 
from dotenv import load_dotenv
import yaml
from google import genai
from google.genai import types
import yfinance as yf

from loader import json_formatter
from ai_client import summary_from_gemini, Gemini_fee



load_dotenv(override=True)
config_path = Path('config.yaml')
config = yaml.safe_load(config_path.read_text(encoding='utf-8'))

### .env, config.yamlで基本設定 ###
API_KEY = os.getenv('GEMINI_API_KEY', None).strip()
PROMPT = config['ai']['prompt']
MODEL = config['ai']['model']
LEVEL = config['ai']['thoughts_level']
DEBUG = config['other']['debug'].lower() in ("true", "1", "t")


def append_csv(path: Path, columns, row: list):
    """pathがなければ作成し、CSVに1行追記"""
    if not path.exists():
        with path.open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(columns)

    with path.open('a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(row)


if __name__ == "__main__":
    ### loader.pyで自動取得に変更予定 ###
    INPUT_DIR = ""

    INPUT_PATH = Path(r"E:\Dev\Projects\chatbot-logger\sample\Claude-Git LF!CRLF line ending issues across platforms (1).json")
    ####################

    AI_LIST = ["Claude-"]

    ai_name = next((p for p in AI_LIST if INPUT_PATH.name.startswith(p)), "Unknown AI")

    raw_data = INPUT_PATH.read_text(encoding="utf-8")
    conversation = "\n".join(json_formatter(raw_data, ai_name))

    GEMINI_ATTRS = {"conversation": conversation, "api_key": API_KEY, "custom_prompt": PROMPT, "model": MODEL, "thoughts_level": LEVEL}

    if DEBUG:
        print(f"Your API Key: ...{API_KEY[-10:]} for {MODEL}")
        
    # GoogleへAPIリクエスト    
    summary, input_tokens, thoughts_tokens, output_tokens = summary_from_gemini(**GEMINI_ATTRS)


    total_output_tokens = thoughts_tokens + output_tokens

    input_fee = Gemini_fee().calculate(MODEL,token_type="input", tokens=input_tokens)
    thoughts_fee = Gemini_fee().calculate(MODEL,token_type="output",tokens=thoughts_tokens)
    output_fee = Gemini_fee().calculate(MODEL,token_type="output",tokens=output_tokens)
    total_output_fee = thoughts_fee + output_fee
    total_fee = input_fee + thoughts_fee + output_fee


    # 為替レートを取得
    ticker = "USDJPY=X"
    dy_rate = yf.Ticker(ticker).history(period="1d").Close[0]
    total_JPY = total_fee * dy_rate
        
    columns = ['conversation', 'AI_name', 'output_text', 'custom_prompt', 'model', 'thinking_budget', 'input_tokens', 'input_fee', 'thoughts_tokens', 'thoughts_fee', 'output_tokens', 'output_fee', 'total_fee', 'total_fee (JPY)']

    record = [INPUT_PATH.name, ai_name, summary, PROMPT, MODEL, LEVEL, input_tokens, input_fee, thoughts_tokens, thoughts_fee, output_tokens, output_fee, total_fee, total_JPY]

    output_dir = Path(config['paths']['output_dir'].strip())
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / (f'summary_{INPUT_PATH.stem}.txt')
    csv_path = output_dir / 'record.csv'

    append_csv(csv_path, columns, record)
    
    summary_path.write_text(summary, encoding="utf-8") 
    if DEBUG:
        print(f"created summary: {summary[:100]}")