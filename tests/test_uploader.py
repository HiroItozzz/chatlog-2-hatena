import os
from pathlib import Path

import pytest
from cha2hatena.hatenablog_poster import GeminiStructure, hatena_uploader, xml_unparser
from dotenv import load_dotenv


def test_uploader():

    load_dotenv(override=True)

    """Uploader統合テスト"""
    # APIキー確認
    KEYS = {
        "client_key": os.getenv("HATENA_CONSUMER_KEY", ""),
        "client_secret": os.getenv("HATENA_CONSUMER_SECRET", ""),
        "resource_owner_key": os.getenv("HATENA_ACCESS_TOKEN", ""),
        "resource_owner_secret": os.getenv("HATENA_ACCESS_TOKEN_SECRET", ""),
        "hatena_entry_url": os.getenv("HATENA_ENTRY_URL", ""),
    }
    for key in KEYS.values():
        print(key[-5:])

    if not all(KEYS.values()):
        pytest.skip("はてなAPIキーが設定されていません")

    # JSON読み込み
    path1 = Path("sample/gemini_structure.json")
    json_text = path1.read_text(encoding="utf-8")
    gemini_structure = GeminiStructure.model_validate_json(json_text)

    # XML生成
    xml = xml_unparser(gemini_structure, is_draft=True)
    # 投稿
    result = hatena_uploader(xml, KEYS)

    assert result["title"] is not None
    assert result["is_draft"] == True  # 下書きかどうか確認


if __name__ == "__main__":
    test_uploader()
