import json
import os
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

from cha2hatena.blog.blog_schema import HatenaResponseSchema, HatenaSecretKeys
from cha2hatena.blog.hatenablog_poster import HatenaBlogPoster


@pytest.fixture
def api_keys():
    KEYS = {
        "hatena_client_key": "c_key",
        "hatena_client_secret": "c_secret",
        "hatena_resource_owner_key": "r_owner_key",
        "hatena_resource_owner_secret": "r_owner_secret",
        "hatena_entry_url": "https://example.com",
    }
    return KEYS


@pytest.mark.asyncio
class TestHatena:
    async def test_uploader(self):
        load_dotenv(override=True)

        """Uploader統合テスト"""
        # APIキー確認
        _keys = {
            "hatena_client_key": os.getenv("HATENA_CONSUMER_KEY", ""),
            "hatena_client_secret": os.getenv("HATENA_CONSUMER_SECRET", ""),
            "hatena_resource_owner_key": os.getenv("HATENA_ACCESS_TOKEN", ""),
            "hatena_resource_owner_secret": os.getenv("HATENA_ACCESS_TOKEN_SECRET", ""),
            "hatena_entry_url": os.getenv("HATENA_ENTRY_URL", ""),
        }
        for key in _keys.values():
            print(key[-5:])

        keys = HatenaSecretKeys.model_validate(_keys)

        client = httpx.AsyncClient()

        # JSON読み込み
        path1 = Path("sample/gemini_structure.json")
        data = json.loads(path1.read_text(encoding="utf-8"))
        poster = HatenaBlogPoster(**data, is_draft=True, hatena_secret_keys=keys)
        # XML生成
        xml = poster.xml_unparser()
        res = await poster.hatena_oauth(xml, client)

        result: HatenaResponseSchema = poster.parse_response(res)

        print(result.url)
        print(result.url_edit)

        assert all(_keys.values())
        assert result.title is not None
        assert result.is_draft  # 下書きかどうか確認
