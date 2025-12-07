import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


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


def validate_config(config_dict: dict, secret_keys: dict):
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
    validate_config(config, secret_keys)

    return config, secret_keys
