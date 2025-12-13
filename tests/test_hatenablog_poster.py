import json
import os
from pathlib import Path

from dotenv import load_dotenv

from cha2hatena.hatenablog_poster import hatena_oauth, parse_response, xml_unparser


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

    # JSON読み込み
    path1 = Path("sample/gemini_structure.json")
    json_text = path1.read_text(encoding="utf-8")
    data = json.loads(json_text)

    # XML生成
    xml = xml_unparser(**data, is_draft=True)
    res = hatena_oauth(xml, hatena_secret_keys=KEYS)

    result = parse_response(res)

    print(result["link_edit"])
    print(result["link_edit_user"])
    print(result["link_alternate"])

    assert all(KEYS.values())
    assert result["title"] is not None
    assert result["is_draft"]  # 下書きかどうか確認


if __name__ == "__main__":
    test_uploader()
