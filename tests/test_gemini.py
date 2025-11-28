import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import yaml
from google import genai
from google.genai import types

# 親ディレクトリをパスに追加
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# これでインポート可能
from loader import json_formatter
from ai_client import summary_from_gemini


load_dotenv()
config_path = Path('config.yaml')
config = yaml.safe_load(config_path.read_text(encoding='utf-8'))

DEBUG = config['other']['debug'].lower() in ("true", "1", "t")


API_KEY = os.getenv('GEMINI_API_KEY', "").strip()

PROMPT = config['ai']['prompt']
MODEL = config['ai']['model']
LEVEL = config['ai']['thoughts_level']


INPUT_PATH = Path('./outputs/Claude-Git LF!CRLF line ending issues across platforms (1).txt')

print(f"カレントディレクトリ: {Path.cwd()}")
print(f"絶対パス: {INPUT_PATH.resolve()}")
print(f"存在する: {INPUT_PATH.exists()}")

TEXT = INPUT_PATH.read_text(encoding="utf-8")


summary, input_token, output_token = summary_from_gemini(text=TEXT, api_key=API_KEY, prompt=PROMPT, model=MODEL, thoughts_level=-1)

print(f"入力； {PROMPT}\n\n{TEXT}\n 出力：{summary}\n\n {len(summary)}文字 \n{input_token}, \n{output_token}")

