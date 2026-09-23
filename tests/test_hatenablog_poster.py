"""はてなブログ投稿のテスト（通信なし）"""

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
import pytest

from cha2hatena.blog.hatenablog_poster import HatenaBlogPoster
from cha2hatena.blog.schema import HatenaSecretKeys

ENTRY_URL = "https://blog.hatena.ne.jp/user/blog.example.com/atom/entry"
NS = {"atom": "http://www.w3.org/2005/Atom", "app": "http://www.w3.org/2007/app"}

RESPONSE_XML = """<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
  <link rel="edit" href="https://blog.hatena.ne.jp/user/blog.example.com/atom/entry/2500000000"/>
  <link rel="alternate" type="text/html" href="https://blog.example.com/entry/2025/11/20/100000"/>
  <author><name>user</name></author>
  <title>記事タイトル</title>
  <updated>2025-11-20T10:00:00+09:00</updated>
  <content type="text/x-markdown">本文</content>
  <category term="Python" />
  <category term="自動投稿" />
  <app:control>
    <app:draft>yes</app:draft>
  </app:control>
</entry>
"""


def make_poster(**overrides) -> HatenaBlogPoster:
    fields = {
        "title": "タイトル",
        "content": "# 見出し\n本文",
        "categories": ["Python", "学習"],
        "preset_categories": ["自動投稿"],
        "is_draft": True,
        "hatena_secret_keys": HatenaSecretKeys(
            hatena_entry_url=ENTRY_URL,
            hatena_client_key="c_key",
            hatena_client_secret="c_secret",
            hatena_resource_owner_key="r_key",
            hatena_resource_owner_secret="r_secret",
        ),
    }
    return HatenaBlogPoster(**(fields | overrides))


def parse_entry(xml_str: str) -> ET.Element:
    return ET.fromstring(xml_str)


# --- リクエストXML ---


def test_request_xml_contains_article():
    root = parse_entry(make_poster().xml_unparser())

    assert root.find("atom:title", NS).text == "タイトル"
    content = root.find("atom:content", NS)
    assert content.text == "# 見出し\n本文"
    assert content.get("type") == "text/x-markdown"


def test_request_xml_merges_preset_categories():
    root = parse_entry(make_poster().xml_unparser())

    terms = [c.get("term") for c in root.findall("atom:category", NS)]
    assert terms == ["Python", "学習", "自動投稿"]


@pytest.mark.parametrize(("is_draft", "expected"), [(True, "yes"), (False, "no")])
def test_request_xml_draft_flag(is_draft, expected):
    root = parse_entry(make_poster(is_draft=is_draft).xml_unparser())

    assert root.find("app:control/app:draft", NS).text == expected


def test_updated_defaults_to_now_in_jst():
    root = parse_entry(make_poster().xml_unparser())

    assert root.find("atom:updated", NS).text.endswith("+09:00")


def test_naive_updated_is_treated_as_jst():
    root = parse_entry(make_poster(updated=datetime(2025, 11, 20, 10, 0)).xml_unparser())  # noqa: DTZ001

    assert root.find("atom:updated", NS).text == "2025-11-20T10:00:00+09:00"


# --- レスポンス解析 ---


def test_parse_response():
    result = HatenaBlogPoster.parse_response(httpx.Response(201, text=RESPONSE_XML))

    assert result.title == "記事タイトル"
    assert result.url == "https://blog.example.com/entry/2025/11/20/100000"
    assert result.url_edit == "https://blog.hatena.ne.jp/user/blog.example.com/edit?entry=2500000000"
    assert result.categories == ["Python", "自動投稿"]
    assert result.is_draft is True
    assert result.status_code == 201


# --- 投稿（MockTransport） ---


@pytest.mark.asyncio
async def test_blog_post_sends_signed_xml_to_entry_url():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, text=RESPONSE_XML)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await make_poster().blog_post(client)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == ENTRY_URL
    assert request.headers["Authorization"].startswith("OAuth ")
    assert 'oauth_consumer_key="c_key"' in request.headers["Authorization"]
    assert parse_entry(request.content.decode()).find("atom:title", NS).text == "タイトル"
    assert result.url == "https://blog.example.com/entry/2025/11/20/100000"
