import os
from pathlib import Path
import json, csv
import time
from datetime import datetime, timedelta 
from dotenv import load_dotenv
import yaml
from google import genai
from google.genai import types

from loader import json_formatter
from ai_client import summary_from_gemini


load_dotenv()
config_path = Path('config.yaml')
config = yaml.safe_load(config_path.read_text(encoding='utf-8'))


### .env, config.yamlで基本設定 ###
API_KEY = os.getenv('GEMINI_API_KEY', "").strip()

PROMPT = config['ai']['prompt']
MODEL = config['ai']['model']
LEVEL = config['ai']['thoughts_level']

DEBUG = config['other']['debug'].lower() in ("true", "1", "t")


def append_csv(path: Path, row: list):
    """CSVに1行追記"""
    with path.open('a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(row)


if __name__ == "__main__":
    ### loader.pyで自動取得に変更予定 ###
    INPUT_DIR = ""

    INPUT_PATH = Path(r"E:\Dev\Projects\chatbot-logger\sample\Claude-Git LF!CRLF line ending issues across platforms (1).json")
    ####################


    with open (INPUT_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)

    base_text = "\n".join(json_formatter(raw_data))

    if DEBUG:
        print(base_text)

    summary, input_token, output_token = summary_from_gemini(text=base_text, api_key=API_KEY, prompt=PROMPT, model=MODEL, thoughts_level=LEVEL)

    record = [PROMPT, INPUT_PATH.name, summary, MODEL, LEVEL, input_token, output_token]

    output_dir = Path(config['paths']['output_dir'].strip())
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / (f'summary_{INPUT_PATH.stem}.txt')
    csv_path = output_dir / 'record.csv'

    if not csv_path.exists():
        columns = 'prompt,base_text,output_text,model,thinking_budget,input_token,output_token\n'
        csv_path.write_text(columns, encoding='utf-8-sig')

    append_csv(csv_path, record)
    
    summary_path.write_text(summary, encoding="utf-8") 
    print(summary)