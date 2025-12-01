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

logger = logging.getLogger(__name__)
load_dotenv(override=True)

# .envのDEBUG項目の存在と値でログレベル判定（暫定）
try:
    DEBUG_ENV = os.environ.get("DEBUG", "False").lower() in ("true", "t", "1")
    initial_level = logging.DEBUG if DEBUG_ENV else logging.INFO
except Exception:
    DEBUG_ENV = False
    initial_level = logging.INFO

logging.basicConfig(
    level=initial_level,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


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


def validate_config(config_dict: dict, seacret_keys: dict):
    """設定ファイルとAPIキーの妥当性を検証"""
    required_keys = ["ai.model", "ai.prompt", "paths.output_dir", "other.debug"]

    # 必須キーの存在確認
    for key in required_keys:
        if get_nested_config(config_dict, key) is None:
            raise ValueError(f"Missing required config: {key}")

    # API_KEYの検証
    for name, seacret_key in seacret_keys.items():
        if len(seacret_key.strip()) == 0:
            raise ValueError(f"{name} is required in environment variables")

    # thoughts_levelの範囲チェック
    thoughts_level = config_dict["ai"]["thoughts_level"]
    if thoughts_level is not None and not (-1 <= thoughts_level <= 24576):
        raise ValueError("ai.thoughts_level must be between -1 and 24576")
    elif (0 <= thoughts_level < 128) and config_dict["ai"]["model"] == "gemini-2.5-pro":
        raise ValueError(
            "ai.thoughts_level must be between 128 and 24576 or -1 forgemini-2.5-pro "
        )


def initialize_config() -> tuple[dict, dict]:
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

    seacret_keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "client_key": os.getenv("HATENA_CONSUMER_KEY", ""),
        "client_secret": os.getenv("HATENA_CONSUMER_SECRET", ""),
        "resource_owner_key": os.getenv("HATENA_ACCESS_TOKEN", ""),
        "resource_owner_secret": os.getenv("HATENA_ACCESS_TOKEN_SECRET", ""),
    }

    # 設定の検証
    validate_config(config, seacret_keys)

    return config, seacret_keys


def append_csv(path: Path, columns: list, row: list):
    """pathがなければ作成し、CSVに1行追記"""
    try:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
        logger.info(f"新しいCSVファイルを作成しました: {path}")

        with path.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        logger.info(f"CSVにデータを追記しました: {path.name}")
    except Exception:
        logger.exception("CSVファイルへの書き込み中にエラーが発生しました。")


def summarize_and_upload(
    gemini_config: dict, hatena_seacret_keys: dict, debug_mode: bool = False
) -> tuple[dict, dict]:

    # GoogleへAPIリクエスト
    blog_parts, gemini_stats = ai_client.get_summary(**gemini_config)

    ##### リファクタ予定：hatena_seacret_keysは現在関数内でconfig呼び出し
    # はてなブログへ投稿
    xml_data = uploader.xml_unparser(
        title=blog_parts.title,  # タイトル
        content=blog_parts.content,  # 本文
        categories=blog_parts.categories + ["自動投稿", "AtomPub"],  # カテゴリ追加指定
        author=blog_parts.author,  # デフォルトははてなID
        updated=blog_parts.updated,  # datetime型, デフォルトは5分後に公開
        is_draft=debug_mode,  # デバッグ時は下書き
    )
    result = uploader.hatena_uploader(xml_data, hatena_seacret_keys)  # 辞書型で返却
    #################################################################

    return result, gemini_stats


def main(
    input_path: Path,
    gemini_config: dict,
    hatena_seacret_keys: dict,
    debug_mode: bool = True,
):

    logger.debug("================================================")
    logger.debug(f"アプリケーションが起動しました。DEBUGモード: {debug_mode}")

    AI_LIST = ["Claude", "Gemini", "ChatGPT"]
    ai_name = next((p for p in AI_LIST if input_path.name.startswith(p)), "Unknown AI")

    conversation = json_loader.json_loader(input_path, ai_name)
    gemini_config["conversation"] = conversation

    # Googleで要約取得 & はてなへ投稿
    result, gemini_stats = summarize_and_upload(
        gemini_config, hatena_seacret_keys, debug_mode=DEBUG
    )

    url = result.get("link_alternate", "")
    title = result.get("title", "")
    content = result.get("content", "")
    categories = result.get("categories", [])

    logger.info(f"はてなブログへの投稿に成功しました。")
    ###### 下書きの場合公開URLへのアクセス不能
    logger.info(f"URL: {url}")
    print("-" * 50)
    print(f"投稿タイトル：{title}")
    print(f"\n{'-' * 20}投稿本文{'-' * 20}")
    print(f"{content[:100]}")
    print("-" * 50)

    gemini_fee = ai_client.Gemini_fee()
    i_fee = gemini_fee.calculate(MODEL, "input", gemini_stats["input_tokens"])
    th_fee = gemini_fee.calculate(MODEL, "output", gemini_stats["thoughts_tokens"])
    o_fee = gemini_fee.calculate(MODEL, "output", gemini_stats["output_tokens"])
    total_fee = i_fee + th_fee + o_fee

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
        "output_letter_count",
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
        input_path.name,
        ai_name,
        url,
        result.get("is_draft"),
        title[:15],
        content[:30],
        ",".join(categories),
        gemini_config["custom_prompt"][:20],
        gemini_config["model"],
        gemini_config["thoughts_level"],
        len(conversation),
        gemini_stats["output_letter_count"],
        gemini_stats["input_tokens"],
        i_fee,
        gemini_stats["thoughts_tokens"],
        th_fee,
        gemini_stats["output_tokens"],
        o_fee,
        total_fee,
        total_JPY,
        "..." + gemini_config["gemini_api_key"][-5:],
    ]

    output_dir = Path(config["paths"]["output_dir"].strip())
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / (f"summary_{input_path.stem}.txt")
    csv_path = output_dir / "record_test.csv"

    append_csv(csv_path, columns, record)

    summary_path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":

    # config.yamlで設定初期化
    try:
        config, SEACRET_KEYS = initialize_config()
    except Exception as e:
        logger.critical(f"CONFIG LOADING ERROR: {e}", exc_info=True)
        sys.exit(1)

    PROMPT = config["ai"]["prompt"]
    MODEL = config["ai"]["model"]
    LEVEL = config["ai"]["thoughts_level"]
    DEBUG_CONFIG = config["other"]["debug"].lower() in ("true", "1", "t")

    # 環境変数の参照結果がFalseの場合のみconfigで上書き
    if DEBUG_ENV:
        DEBUG = DEBUG_ENV
    else:
        DEBUG = DEBUG_CONFIG
        if DEBUG:
            logging.getLogger().setLevel(logging.DEBUG)

    GEMINI_CONFIG = {
        "custom_prompt": PROMPT,
        "model": MODEL,
        "thoughts_level": LEVEL,
        "gemini_api_key": SEACRET_KEYS.pop("GEMINI_API_KEY"),
    }
    HATENA_SECRET_KEYS = SEACRET_KEYS

    try:
        if len(sys.argv) > 1:
            input_path = Path(sys.argv[1])
            logger.info(f"処理を開始します: {input_path.name}")
        else:
            logger.info("エラー: ファイル名が正しくありません。実行を終了します")
            sys.exit(1)

        exit_code = main(
            input_path, GEMINI_CONFIG, HATENA_SECRET_KEYS, debug_mode=DEBUG
        )

        logger.info("アプリケーションは正常に終了しました。")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(
            "エラーが発生しました。app.logで詳細を確認してください。\n実行を終了します。",
            exc_info=True,
        )
        sys.exit(1)
