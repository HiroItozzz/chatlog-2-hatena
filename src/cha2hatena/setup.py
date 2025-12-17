import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .llm.conversational_ai import LlmConfig

logger = logging.getLogger(__name__)
load_dotenv(override=True)


def config_validation(config_dict: dict, secret_keys: dict) -> tuple[dict, dict]:
    """設定ファイルとAPIキーの妥当性を検証"""

    # output_dirのデフォルト値設定
    if not config_dict.get("paths", {}).get("output_dir"):
        if "paths" not in config_dict:
            config_dict["paths"] = {}
        config_dict["paths"]["output_dir"] = "outputs"

    # API_KEYの検証
    for idx, (name, secret_key) in enumerate(secret_keys.items()):
        if len(secret_key.strip()) == 0 or secret_key.strip().lower().startswith("your"):
            if idx == 0:
                raise ValueError(f"{name}が見つかりませんでした。.envでキーを設定する必要があります。")
            elif 0 < idx <= 2:
                logger.warning(f"{name}が見つかりませんでした。Geminiによる要約を試みます。")
                break
            elif 2 < idx <= 4:
                logger.warning(
                    f"{name}が見つかりませんでした。ブログを投稿するにははてなブログの初回認証を行う必要があります。"
                )
                logger.warning("Geminiによる要約を試みます。")
                break
            else:
                logger.warning(f"{name}が見つかりませんでした。要約をはてなブログへ投稿します。")

    return config_dict, secret_keys


def config_setup() -> tuple[dict, dict]:
    """設定の初期化と検証"""

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

    try:
        model = config["ai"]["model"]
    except KeyError:
        raise ValueError("ai.modelが設定されていません。config.yamlで設定してください。")
    if model.startswith("deepseek"):
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
    elif model.startswith("gemini"):
        api_key = os.getenv("GEMINI_API_KEY", "")
    else:
        logging.critical("モデル名が正しくありません。実行を中止します。")
        logging.critical(f"モデル名：{model}")

    secret_keys = {
        "API_KEY": api_key,
        "client_key": os.getenv("HATENA_CONSUMER_KEY", ""),
        "client_secret": os.getenv("HATENA_CONSUMER_SECRET", ""),
        "resource_owner_key": os.getenv("HATENA_ACCESS_TOKEN", ""),
        "resource_owner_secret": os.getenv("HATENA_ACCESS_TOKEN_SECRET", ""),
        "hatena_entry_url": os.getenv("HATENA_ENTRY_URL", ""),
        "LINE_CHANNEL_ACCESS_TOKEN": os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
    }

    # 設定の検証
    config_validation(config, secret_keys)

    return config, secret_keys


def log_setup(logger: logging.Logger, initial_level: int, console_format: str) -> tuple:
    """ハンドラー設定"""

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(console_format))
    stream_handler.setLevel(initial_level)
    file_handler = RotatingFileHandler("app.log", maxBytes=int(0.5 * 1024 * 1024), backupCount=1, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    file_handler.setLevel(logging.DEBUG)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return stream_handler, file_handler


def initialization(logger: logging.Logger) -> tuple:
    """DEBUGモード判定、ログレベル決定"""

    # DEBUGモード・ログレベル仮判定
    DEBUG_ENV = os.getenv("DEBUG", "False").lower() in ("true", "t", "1")

    if DEBUG_ENV:
        console_format = "%(levelname)s - %(name)s - %(message)s"
        initial_level = logging.DEBUG
    else:
        console_format = "%(message)s"
        initial_level = logging.WARNING

    # ハンドラー設定
    stream_handler, file_handler = log_setup(logger, initial_level, console_format)

    # 設定読み込み
    config, secret_keys = config_setup()

    llm_config = LlmConfig(
        prompt=config["ai"]["prompt"],
        model=config["ai"]["model"],
        temperature=config["ai"]["temperature"],
        api_key=secret_keys.pop("API_KEY"),
        conversation="",
    )

    # DEBUGモード・ログレベル判定
    DEBUG_CONFIG = config.get("other", {}).get("debug").lower() in ("true", "1", "t")
    DEBUG = DEBUG_ENV if DEBUG_ENV else DEBUG_CONFIG
    if DEBUG and not DEBUG_ENV:
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(logging.Formatter("%(levelname)s - %(name)s - %(message)s"))

    return DEBUG, secret_keys, llm_config, config
