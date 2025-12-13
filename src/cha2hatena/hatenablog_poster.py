import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from requests import Response
from requests_oauthlib import OAuth1Session

logger = logging.getLogger(__name__)


def safe_find(root: ET.Element, key: str, ns: dict | None = None, default: str = "") -> str:
    """ヘルパー関数: Noneの場合返却を空文字に"""
    elem = root.find(key, ns)
    return elem.text if elem is not None else default


def safe_find_attr(root: ET.Element, key: str, attr: str, ns: dict | None = None, default: str = "") -> str:
    """属性取得用ヘルパー関数"""
    elem = root.find(key, ns)
    return elem.get(attr) if elem is not None else default


def xml_unparser(
    title: str,
    content: str,
    categories: list,
    preset_categories: list = [],
    author: str | None = None,
    updated: datetime | None = None,
    is_draft: bool = False,
) -> str:
    """はてなブログ投稿リクエストの形式へ変換"""

    logger.debug(f"{'=' * 25}xml_unparserの処理開始{'=' * 25}")

    # 公開時刻設定
    jst = timezone(timedelta(hours=9))
    if updated is None:
        updated = datetime.now(jst)
    elif updated.tzinfo is None:
        updated = updated.replace(tzinfo=jst)  # timezoneなしの場合JST

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
    for cat in categories + preset_categories:
        ET.SubElement(ROOT, "category", attrib={"term": cat})

    TITLE.text = title
    UPDATED.text = updated.isoformat()  # timezoneありの場合それに従う
    NAME.text = author
    CONTENT.text = content
    DRAFT.text = "yes" if is_draft else "no"
    PREVIEW.text = "no"

    logger.debug(f"{'=' * 25}☑ xml_unparserの処理終了{'=' * 25}")
    return ET.tostring(ROOT, encoding="unicode")


def hatena_oauth(xml_str: str, hatena_secret_keys: dict) -> dict:
    """はてなブログへ投稿"""

    URL = hatena_secret_keys.pop("hatena_entry_url")
    oauth = OAuth1Session(**hatena_secret_keys)
    response = oauth.post(URL, data=xml_str, headers={"Content-Type": "application/xml; charset=utf-8"})

    logger.debug(f"Status: {response.status_code}")
    if response.status_code == 201:
        logger.warning("✓ はてなブログへ投稿成功")
    else:
        logger.error("✗ リクエスト中にエラー発生。はてなブログへ投稿できませんでした。")
    return response


def parse_response(response: Response) -> dict[str, Any]:
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


def blog_post(
    title: str,
    content: str,
    categories: list,
    hatena_secret_keys: dict,
    preset_categories: list = [],
    author: str | None = None,
    updated: datetime | None = None,
    is_draft: bool = False,
) -> dict:
    xml_entry = xml_unparser(title, content, categories, preset_categories, author, updated, is_draft)
    res = hatena_oauth(xml_entry, hatena_secret_keys)

    return parse_response(res)
