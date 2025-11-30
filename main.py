import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import ai_client
import json_loader
import uploader
import yaml
import yfinance as yf
from dotenv import load_dotenv

# .envでログレベル判定。ただし最終決定はconfigを見てメイン処理内で実行
try:
    IS_DEBUG_MODE_ENV = os.environ.get("DEBUG", "False").lower() in ("true", "t", "1")
    initial_level = logging.DEBUG if IS_DEBUG_MODE_ENV else logging.INFO
except Exception:
    initial_level = logging.INFO

# 設定
logging.basicConfig(
    level=initial_level,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

###########################################################


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


############################################################


def append_csv(path: Path, columns, row: list, logger: logging.Logger):
    """pathがなければ作成し、CSVに1行追記"""
    try:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
        logger.debug(f"新しいCSVファイルを作成しました: {path}")

        with path.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        logger.debug(f"CSVにデータを追記しました: {path.name}")
    except Exception:
        logger.exception("CSVファイルへの書き込み中にエラーが発生しました。")


if __name__ == "__main__":

    # config.yamlで設定初期化
    try:
        config, API_KEY, PROMPT, MODEL, LEVEL, DEBUG = initialize_config()
    except Exception as e:
        print(f"CONFIG LOADING ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # configでDEBUGモードの場合のみ.envによる設定を上書き
    if DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.info("================================================")
    logger.info(f"アプリケーションが起動しました。DEBUGモード: {DEBUG}")

    ### uploader.pyで自動取得に変更予定 ###
    # コマンドライン引数からファイル名を取得する
    if len(sys.argv) > 1:
        INPUT_PATH = Path(sys.argv[1])
        logger.info(f"処理を開始します: {INPUT_PATH.name}")
    else:
        # 引数がなければエラーメッセージを表示
        print("エラー: ファイル名が正しくありません。実行を終了します")
        sys.exit(1)
    ####################################

    try:
        AI_LIST = ["Claude", "Gemini", "ChatGPT"]
        ai_name = next(
            (p for p in AI_LIST if INPUT_PATH.name.startswith(p)), "Unknown AI"
        )
        conversation = json_loader.json_loader(INPUT_PATH)

        logger.info(f"Your API Key: ...{API_KEY[-5:]} for {MODEL}")

        GEMINI_ATTRS = {
            "conversation": conversation,
            "api_key": API_KEY,
            "custom_prompt": PROMPT,
            "model": MODEL,
            "thoughts_level": LEVEL,
        }

        # GoogleへAPIリクエスト
        blog_parts, stats = ai_client.get_summary(**GEMINI_ATTRS)

        xml_data = uploader.xml_unparser(
            title=blog_parts.title,
            content=blog_parts.content,
            categories=blog_parts.categories + ["自動投稿", "AtomPub"],
            author=blog_parts.author,
            updated=blog_parts.updated,
        )

        result_dict = uploader.hatena_uploader(xml_data)  # 辞書型で返却
        entry_url = result_dict.get("link_alternate", "")
        entry_title = result_dict.get("title", "")
        entry_content = result_dict.get("content", "")
        categories = result_dict.get("categories", [])

        logger.info(f"はてなブログへの投稿に成功しました。")
        logger.info(f"URL: {entry_url}")
        logger.info("-" * 50)
        logger.info(f"投稿タイトル：{entry_title}")
        logger.info(f"\n{"-" * 20}投稿本文{"-" * 20}")
        logger.info(f"{entry_content[:100]}")
        logger.info("-" * 50)

        i_tokens = stats["input_tokens"]
        th_tokens = stats["thoughts_tokens"]
        o_tokens = stats["output_tokens"]

        gemini_fee = ai_client.Gemini_fee()
        input_fee = gemini_fee.calculate(MODEL, token_type="input", tokens=i_tokens)
        thoughts_fee = gemini_fee.calculate(
            MODEL, token_type="output", tokens=th_tokens
        )
        output_fee = gemini_fee.calculate(MODEL, token_type="output", tokens=o_tokens)

        total_output_fee = thoughts_fee + output_fee
        total_fee = input_fee + total_output_fee
        ###############

        # 為替レートを取得
        ticker = "USDJPY=X"
        dy_rate = yf.Ticker(ticker).history(period="1d").Close.iloc[0]
        total_JPY = total_fee * dy_rate

        columns = [
            "timestamp",
            "conversation",
            "AI_name",
            "entry_URL",
            "is_draft",
            "entry_title",
            "entry_content",
            "categories",
            "custom_prompt",
            "model",
            "thinking_budget",
            "input_letter_count",
            "input_tokens",
            "input_fee",
            "thoughts_tokens",
            "thoughts_fee",
            "output_tokens",
            "output_fee",
            "total_fee (USD)",
            "total_fee (JPY)",
            "api_key",
        ]

        record = [
            datetime.now().isoformat(),
            INPUT_PATH.name,
            ai_name,
            entry_url,
            result_dict.get("is_draft"),
            entry_title,
            entry_content[:30],
            ",".join(categories),
            PROMPT,
            MODEL,
            LEVEL,
            len(conversation),
            i_tokens,
            input_fee,
            th_tokens,
            thoughts_fee,
            o_tokens,
            output_fee,
            total_fee,
            total_JPY,
            API_KEY[-5:],
        ]

        output_dir = Path(config["paths"]["output_dir"].strip())
        output_dir.mkdir(exist_ok=True)
        summary_path = output_dir / (f"summary_{INPUT_PATH.stem}.txt")
        csv_path = output_dir / "record_test.csv"

        append_csv(csv_path, columns, record, logger)

        summary_path.write_text(blog_parts.content, encoding="utf-8")
        logger.info(f"created summary: {blog_parts.content[:100]}")

    except Exception as e:
        logger.critical(
            "重大なエラーが発生しました。app.logで詳細を確認してください。\n実行を終了します。",
            exc_info=True,
        )
        sys.exit(1)

    logger.info("アプリケーションは正常に終了しました。")
