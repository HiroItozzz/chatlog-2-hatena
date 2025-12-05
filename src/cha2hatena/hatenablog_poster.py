import logging
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from requests_oauthlib import OAuth1Session

logger = logging.getLogger(__name__)


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

    logger.debug(f"{'='*25}xml_unparserの処理開始{'='*25}")

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

    logger.debug(f"{'='*25}☑ xml_unparserの処理終了{'='*25}")
    return ET.tostring(ROOT, encoding="unicode")


def hatena_oauth(xml_str: str, hatena_secret_keys: dict) -> dict:
    """はてなブログへ投稿"""

    URL = hatena_secret_keys.pop("hatena_entry_url")
    oauth = OAuth1Session(**hatena_secret_keys)
    response = oauth.post(
        URL, data=xml_str, headers={"Content-Type": "application/xml; charset=utf-8"}
    )

    logger.debug(f"Status: {response.status_code}")
    if response.status_code == 201:
        logger.info("✓ はてなブログへ投稿成功")
    else:
        logger.info(f"✗ エラー発生。はてなブログへ投稿できませんでした。")

        ### エラー処理考え中
        raise ConnectionError

    return response


def parse_response(response: str) -> dict:
    """投稿結果を取得"""

    # 名前空間
    NS = {"atom": "http://www.w3.org/2005/Atom", "app": "http://www.w3.org/2007/app"}

    root = ET.fromstring(response.text)
    categories = []
    for category_elem in root.findall("atom:category", NS):
        term = category_elem.get("term")
        if term:
            categories.append(term)

    response_dict = {
        # Atom名前空間の要素
        "title": root.find("{http://www.w3.org/2005/Atom}title").text,
        "author": root.find("atom:author/atom:name", NS).text,
        "content": root.find("atom:content", NS).text,
        "time": datetime.fromisoformat(root.find("atom:updated", NS).text),
        "link_edit": root.find("atom:link[@rel='edit']", NS).get("href"),
        "link_alternate": root.find("atom:link[@rel='alternate']", NS).get("href"),
        "categories": categories,
        # app名前空間の要素
        "is_draft": root.find("app:control/app:draft", NS).text == "yes",
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

    xml_entry = xml_unparser(
        title, content, categories, preset_categories, author, updated, is_draft
    )
    res = hatena_oauth(xml_entry, hatena_secret_keys)

    return parse_response(res)
