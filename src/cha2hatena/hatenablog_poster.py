import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from authlib.integrations.httpx_client import OAuth1Auth
from pydantic import ConfigDict, Field

from .blog_schema import AbstractBlogPoster, HatenaSecretKeys

logger = logging.getLogger(__name__)


def safe_find(root: ET.Element, key: str, ns: dict | None = None, default: str = "") -> str:
    """ヘルパー関数: Noneの場合返却を空文字に"""
    elem = root.find(key, ns)
    return elem.text if elem is not None else default


def safe_find_attr(root: ET.Element, key: str, attr: str, ns: dict | None = None, default: str = "") -> str:
    """属性取得用ヘルパー関数"""
    elem = root.find(key, ns)
    return elem.get(attr) if elem is not None else default


class HatenaBlogPoster(AbstractBlogPoster):

    title: str
    content: str
    categories: list
    preset_categories: list = []
    secret_keys: HatenaSecretKeys = Field(alias="hatena_secret_keys")
    author: str | None = None
    updated: datetime | None = None
    is_draft: bool = False

    async def blog_post(self, httpx_client: httpx.AsyncClient) -> dict:
        xml_entry = self.xml_unparser()
        res = await self.hatena_oauth(xml_entry, httpx_client)

        return self.parse_response(res)

    def xml_unparser(self) -> str:
        """はてなブログ投稿リクエストの形式へ変換"""

        logger.debug(f"{'=' * 25}xml_unparserの処理開始{'=' * 25}")

        # 公開時刻設定
        jst = timezone(timedelta(hours=9))
        if self.updated is None:
            self.updated = datetime.now(jst)
        elif self.updated.tzinfo is None:
            self.updated = self.updated.replace(tzinfo=jst)  # timezoneなしの場合JST

        ROOT = ET.Element(
            "entry",
            attrib={
                "xmlns": "http://www.w3.org/2005/Atom",
                "xmlns:app": "http://www.w3.org/2007/app",
            },
        )
        TITLE = ET.SubElement(ROOT, "title")
        UPDATED = ET.SubElement(ROOT, "updated")
        AUTHOR = ET.SubElement(ROOT, "author")
        NAME = ET.SubElement(AUTHOR, "name")
        CONTENT = ET.SubElement(ROOT, "content", attrib={"type": "text/x-markdown"})
        CONTROL = ET.SubElement(ROOT, "app:control")
        DRAFT = ET.SubElement(CONTROL, "app:draft")
        PREVIEW = ET.SubElement(CONTROL, "app:preview")
        for cat in self.categories + self.preset_categories:
            ET.SubElement(ROOT, "category", attrib={"term": cat})

        TITLE.text = self.title
        UPDATED.text = self.updated.isoformat()  # timezoneありの場合それに従う
        NAME.text = self.author
        CONTENT.text = self.content
        DRAFT.text = "yes" if self.is_draft else "no"
        PREVIEW.text = "no"

        logger.debug(f"{'=' * 25}☑ xml_unparserの処理終了{'=' * 25}")
        return ET.tostring(ROOT, encoding="unicode")

    async def hatena_oauth(self, xml_str: str, httpx_client: httpx.AsyncClient) -> dict:
        """はてなブログへ投稿"""

        URL = self.secret_keys.model_dump().get("hatena_entry_url")
        auth = OAuth1Auth(
            **self.secret_keys.get_auth_params(),
            force_include_body=True,  # ← これを追加
        )
        response = await httpx_client.post(
            URL, auth=auth, content=xml_str, headers={"Content-Type": "application/xml; charset=utf-8"}
        )

        logger.debug(f"Status: {response.status_code}")
        if response.status_code == 201:
            logger.warning("✓ はてなブログへ投稿成功")
        else:
            logger.error("✗ リクエスト中にエラー発生。はてなブログへ投稿できませんでした。")
        return response

    @staticmethod
    def parse_response(response: httpx.Response) -> dict[str, Any]:
        """投稿結果を取得"""

        # 名前空間
        NS = {"atom": "http://www.w3.org/2005/Atom", "app": "http://www.w3.org/2007/app"}

        root = ET.fromstring(response.text)
        categories = []
        for category_elem in root.findall("atom:category", NS):
            term = category_elem.get("term", "")
            if term:
                categories.append(term)
        link_edit = safe_find_attr(root, "atom:link[@rel='edit']", "href", NS)
        link_edit_user = str(link_edit).replace("atom/entry/", "edit?entry=")

        response_dict = {
            "status_code": response.status_code,
            # Atom名前空間の要素
            "title": safe_find(root, "{http://www.w3.org/2005/Atom}title"),  # XML名前空間の実体
            "author": safe_find(root, "atom:author/atom:name", NS),
            "content": safe_find(root, "atom:content", NS),
            "time": datetime.fromisoformat(safe_find(root, "atom:updated", NS)),
            "link_edit": link_edit,
            "link_edit_user": link_edit_user,
            "link_alternate": safe_find_attr(root, "atom:link[@rel='alternate']", "href", NS),
            "categories": categories,
            # app名前空間の要素
            "is_draft": safe_find(root, "app:control/app:draft", NS) == "yes",
        }

        return response_dict
