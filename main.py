import csv
import os
from datetime import datetime
from pathlib import Path

import yaml
import yfinance as yf
from ai_client import Gemini_fee, summary_from_gemini
from dotenv import load_dotenv
from json_loader import json_loader
from uploader import hatena_uploader, xml_unparser



def get_nested_config(config_dict, key_path):
    """ネストした設定値を取得 (例: 'ai.model' -> config['ai']['model'])"""
    keys = key_path.split(".")
    value = config_dict
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return None


def validate_config(config_dict, api_key):
    """設定ファイルとAPIキーの妥当性を検証"""
    required_keys = ["ai.model", "ai.prompt", "paths.output_dir", "other.debug"]

    # 必須キーの存在確認
    for key in required_keys:
        if get_nested_config(config_dict, key) is None:
            raise ValueError(f"Missing required config: {key}")

    # API_KEYの検証
    if not api_key or len(api_key.strip()) == 0:
        raise ValueError("GEMINI_API_KEY is required in environment variables")

    # thoughts_levelの範囲チェック
    thoughts_level = config_dict["ai"]["thoughts_level"]
    if thoughts_level is not None and not (-1 <= thoughts_level <= 24576):
        raise ValueError("ai.thoughts_level must be between -1 and 24576")
    elif (0 <= thoughts_level < 128) and config_dict["ai"]["model"] == "gemini-2.5-pro":
        raise ValueError(
            "ai.thoughts_level must be between 128 and 24576 or -1 forgemini-2.5-pro "
        )


def initialize_config():
    """設定の初期化と検証"""
    load_dotenv(override=True)
    config_path = Path("config.yaml")

    # 設定ファイルの読み込みとエラーハンドリング
    try:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config is None:
            raise ValueError("Config file is empty or invalid YAML")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in config file: {e}")

    ### .env, config.yamlで基本設定 ###
    api_key_raw = os.getenv("GEMINI_API_KEY")
    API_KEY = api_key_raw.strip() if api_key_raw else None

    # 設定の検証
    validate_config(config, API_KEY)

    PROMPT = config["ai"]["prompt"]
    MODEL = config["ai"]["model"]
    LEVEL = config["ai"]["thoughts_level"]
    DEBUG = config["other"]["debug"].lower() in ("true", "1", "t")

    return config, API_KEY, PROMPT, MODEL, LEVEL, DEBUG



def append_csv(path: Path, columns, row: list):
    """pathがなければ作成し、CSVに1行追記"""
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)

    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(row)


if __name__ == "__main__":
    # 設定初期化
    config, API_KEY, PROMPT, MODEL, LEVEL, DEBUG = initialize_config()

    ### loader.pyで自動取得に変更予定 ###
    INPUT_PATH = Path(
        r"E:\Dev\Projects\chatbot-logger\sample\Claude-Git LF!CRLF line ending issues across platforms (1).json"
    )
    ####################

    AI_LIST = ["Claude", "Gemini", "ChatGPT"]
    ai_name = next((p for p in AI_LIST if INPUT_PATH.name.startswith(p)), "Unknown AI")
    conversation = json_loader(INPUT_PATH)

    if DEBUG:
        print(f"Your API Key: ...{API_KEY[-5:]} for {MODEL}")

    GEMINI_ATTRS = {
        "conversation": conversation,
        "api_key": API_KEY,
        "custom_prompt": PROMPT,
        "model": MODEL,
        "thoughts_level": LEVEL,
    }
    blog_parts, stats = summary_from_gemini(**GEMINI_ATTRS)  # GoogleへAPIリクエスト

    xml_data = xml_unparser(
        title=blog_parts.title,
        content=blog_parts.content,
        categories=blog_parts.categories,
        author=blog_parts.author,
        updated=blog_parts.updated,
    )

    result = hatena_uploader(xml_data)  # 辞書型で返却
    print(f"投稿に成功しました。\nタイトル：{result["title"]}")
    print(f"\n{"-" * 15}本文{"-" * 15}")
    print(f"{result["content"]["#text"]}")

    ####### 関数化？
    i_tokens = stats["input_tokens"]
    th_tokens = stats["thoughts_tokens"]
    o_tokens = stats["output_tokens"]
    total_output_tokens = th_tokens + o_tokens

    input_fee = Gemini_fee().calculate(MODEL, token_type="input", tokens=i_tokens)
    thoughts_fee = Gemini_fee().calculate(MODEL, token_type="output", tokens=th_tokens)
    output_fee = Gemini_fee().calculate(MODEL, token_type="output", tokens=o_tokens)
    total_output_fee = thoughts_fee + output_fee
    total_fee = input_fee + thoughts_fee + output_fee
    ###############

    # 為替レートを取得
    ticker = "USDJPY=X"
    dy_rate = yf.Ticker(ticker).history(period="1d").Close[0]
    total_JPY = total_fee * dy_rate

    columns = [
        "conversation",
        "AI_name",
        "output_text",
        "custom_prompt",
        "model",
        "thinking_budget",
        "input_tokens",
        "input_fee",
        "thoughts_tokens",
        "thoughts_fee",
        "output_tokens",
        "output_fee",
        "total_fee",
        "total_fee (JPY)",
    ]

    record = [
        INPUT_PATH.name,
        ai_name,
        blog_parts.content,
        PROMPT,
        MODEL,
        LEVEL,
        i_tokens,
        input_fee,
        th_tokens,
        thoughts_fee,
        o_tokens,
        output_fee,
        total_fee,
        total_JPY,
    ]

    output_dir = Path(config["paths"]["output_dir"].strip())
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / (f"summary_{INPUT_PATH.stem}.txt")
    csv_path = output_dir / "record_test.csv"

    append_csv(csv_path, columns, record)

    summary_path.write_text(blog_parts.content, encoding="utf-8")
    if DEBUG:
        print(f"created summary: {blog_parts.content[:100]}")
