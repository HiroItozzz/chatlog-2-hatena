"""Qiita / Dev.to 投稿のテスト（通信なし）"""

import json
from pathlib import Path

import httpx
import pytest

from cha2hatena.blog.devto_poster import DevToPoster
from cha2hatena.blog.qiita_poster import QiitaPoster

SAMPLE_DIR = Path(__file__).parent.parent / "sample"


def common_fields(**overrides) -> dict:
    """各ポスターに共通で渡される記事データ"""
    fields = {
        "title": "タイトル",
        "content": "本文",
        "categories": ["Python", "学習"],
        "preset_categories": ["自動投稿"],
        "is_draft": True,
    }
    return fields | overrides


def recording_client(requests: list[httpx.Request], response_file: str, status: int = 201) -> httpx.AsyncClient:
    body = (SAMPLE_DIR / response_file).read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, text=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --- Qiita ---


def test_qiita_parse_response():
    body = (SAMPLE_DIR / "qiita_res_success.json").read_text(encoding="utf-8")
    result = QiitaPoster.parse_response(httpx.Response(201, text=body))

    assert result.title == "テスト実行中"
    assert result.url.startswith("https://qiita.com/")
    assert result.categories == ["自動投稿", "カテゴリ1", "カテゴリー2", "カテゴリー3"]
    assert result.is_draft is True
    assert result.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("is_draft", [True, False])
async def test_qiita_blog_post_request(is_draft):
    requests: list[httpx.Request] = []
    poster = QiitaPoster(**common_fields(is_draft=is_draft), qiita_bearer_token="q_token")

    async with recording_client(requests, "qiita_res_success.json") as client:
        await poster.blog_post(client)

    request = requests[0]
    payload = json.loads(request.content)
    assert str(request.url) == "https://qiita.com/api/v2/items"
    assert request.headers["Authorization"] == "Bearer q_token"
    assert payload["title"] == "タイトル"
    assert payload["body"] == "本文"
    assert payload["private"] is is_draft
    assert [t["name"] for t in payload["tags"]] == ["Python", "学習", "自動投稿"]
    assert "q_token" not in request.content.decode()


# --- Dev.to ---


@pytest.mark.parametrize(
    ("response_file", "is_draft"),
    [("devto_res_draft.json", True), ("devto_res_publish.json", False)],
)
def test_devto_parse_response(response_file, is_draft):
    body = (SAMPLE_DIR / response_file).read_text(encoding="utf-8")
    result = DevToPoster.parse_response(httpx.Response(201, text=body))

    assert result.title == "テスト実行中"
    assert result.url.startswith("https://dev.to/")
    assert result.is_draft is is_draft
    assert result.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("is_draft", [True, False])
async def test_devto_blog_post_request(is_draft):
    requests: list[httpx.Request] = []
    poster = DevToPoster(**common_fields(is_draft=is_draft), devto_api_key="d_key")

    async with recording_client(requests, "devto_res_draft.json") as client:
        await poster.blog_post(client)

    request = requests[0]
    article = json.loads(request.content)["article"]
    assert str(request.url) == "https://dev.to/api/articles"
    assert request.headers["api-key"] == "d_key"
    assert article["title"] == "タイトル"
    assert article["body_markdown"] == "本文"
    assert article["published"] is (not is_draft)
    assert article["tags"] == ["Python", "学習", "自動投稿"]
    assert "d_key" not in request.content.decode()


def test_devto_tags_are_limited_to_four():
    poster = DevToPoster(
        **common_fields(categories=["a", "b", "c", "d"], preset_categories=["preset"]),
        devto_api_key="d_key",
    )

    assert poster.tags == ["a", "b", "c", "d"]
