import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv(override=True)

def get_nested_config(config_dict:dict, key_path:Path)-> str | None:
    """ネストした設定値を取得 (例: 'ai.model' -> config['ai']['model'])"""

    keys = key_path.split(".")
    value = config_dict
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return None


def config_validation(config_dict: dict, secret_keys: dict) -> tuple[dict,dict]:
    """設定ファイルとAPIキーの妥当性を検証"""

    required_keys = ["ai.model", "ai.prompt", "paths.output_dir", "other.debug"]

    # 必須キーの存在確認
    for key in required_keys:
        if get_nested_config(config_dict, key) is None:
            raise ValueError(f"{key}が見つかりません。config.yamlで設定をする必要があります。")

    # API_KEYの検証
    for idx, (name, secret_key) in enumerate(secret_keys.items()):
        if len(secret_key.strip()) == 0 or secret_key.strip().lower().startswith("your"):
            if idx == 0:
                raise ValueError(f"{name}が見つかりませんでした。.envでキーを設定する必要があります。")
            elif 0 < idx <= 2:
                logger.warning(f"{name}が見つかりませんでした。Geminiによる要約を試みます。")
                break
            elif 2 < idx <= 4:
                logger.warning(f"{name}が見つかりませんでした。ブログを投稿するにははてなブログの初回認証を行う必要があります。")
                logger.warning("Geminiによる要約を試みます。")
                break
            else:
                logger.warning(f"{name}が見つかりませんでした。要約をはてなブログへ投稿します。")

    # thoughts_levelの範囲チェック
    thoughts_level = config_dict["ai"]["thoughts_level"]
    if thoughts_level is not None and not (-1 <= thoughts_level <= 24576):
        raise ValueError("ai.thoughts_level must be between -1 and 24576")
    elif (0 <= thoughts_level < 128) and config_dict["ai"]["model"] == "gemini-2.5-pro":
        raise ValueError("ai.thoughts_level must be between 128 and 24576 or -1 forgemini-2.5-pro ")

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

    secret_keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
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


def log_setup(logger:logging.Logger, initial_level:int, console_format:str) ->tuple:
    '''ハンドラー設定'''

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(console_format))
    stream_handler.setLevel(initial_level)
    file_handler = RotatingFileHandler("app.log", maxBytes=int(0.5*1024*1024), backupCount=1 ,encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    file_handler.setLevel(logging.DEBUG)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return stream_handler, file_handler


def initialization(logger:logging.Logger) ->tuple:
    '''DEBUGモード判定、ログレベル決定'''
    
    # DEBUGモード・ログレベル仮判定
    try:
        DEBUG_ENV = os.getenv("DEBUG", "False").lower() in ("true", "t", "1")
        initial_level = logging.DEBUG if DEBUG_ENV else logging.WARNING
        console_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    except Exception:
        DEBUG_ENV = False
        initial_level = logging.WARNING
        console_format = "%(message)s"

    # ハンドラー設定
    stream_handler, file_handler = log_setup(logger,initial_level, console_format)

    # 設定読み込み
    config, secret_keys = config_setup()
    
    # DEBUGモード・ログレベル判定
    DEBUG_CONFIG = config["other"]["debug"].lower() in ("true", "1", "t")
    DEBUG = DEBUG_ENV if DEBUG_ENV else DEBUG_CONFIG
    if DEBUG and not DEBUG_ENV:
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    return DEBUG, secret_keys, config,  stream_handler, file_handler