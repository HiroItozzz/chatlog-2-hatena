import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import xmltodict
import yaml
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv(override=True)
config_path = Path("config.yaml")
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

DEBUG = config["other"]["debug"].lower() in ("true", "1", "t")


entry_xml = r"""<?xml version="1.0" encoding="utf-8"?>

<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>TITLE</title>
  <updated>2013-09-02T11:28:23+09:00</updated>  # 未来の投稿の場合指定
  <author><name>name</name></author>
  <content type="text/plain">
    ===========CONTENT===========
  </content>
  <category term="Scala" />
  <app:control>
    <app:draft>yes</app:draft> # 下書きの場合
    <app:preview>no</app:preview> #
  </app:control>
</entry>"""


def xml_unparser(
    title: str,
    content: str,
    categories: list | None = None,
    author: str | None = None,
    updated: datetime | None = None,
) -> str:

    if categories is None:
        categories = ["Python", "自動投稿"]

    jst = timezone(timedelta(hours=9))
    if updated is None:
        updated = datetime.now(jst) + timedelta(minutes=5)  # デフォルトで5分後に設定
    elif updated.tzinfo is None:
        updated = updated.replace(tzinfo=jst)  # timezoneなしの場合jst指定

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
    for cat in categories:
        ET.SubElement(ROOT, "category", attrib={"term": cat})

    TITLE.text = title
    UPDATED.text = updated.isoformat()  # timezoneありの場合それに従う
    NAME.text = author
    CONTENT.text = content
    DRAFT.text = "no"
    PREVIEW.text = "no"

    if DEBUG:
        DRAFT.text = "yes"

    return ET.tostring(ROOT, encoding="unicode")


def uploader(entry_xml: str = None) -> dict:
    URL = os.getenv(
        "HATENA_BASE_URL", None
    ).strip()  # https://blog.hatena.ne.jp/{はてなID}/{ブログID}/atom/

    # 環境変数を読み込み
    CONSUMER_KEY = os.getenv("HATENA_CONSUMER_KEY", None).strip()
    CONSUMER_SECRET = os.getenv("HATENA_CONSUMER_SECRET", None).strip()
    ACCESS_TOKEN = os.getenv("HATENA_ACCESS_TOKEN", None).strip()
    ACCESS_TOKEN_SECRET = os.getenv("HATENA_ACCESS_TOKEN_SECRET", None).strip()

    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    response = oauth.post(
        URL, data=entry_xml, headers={"Content-Type": "application/xml; charset=utf-8"}
    )

    if DEBUG:
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            print("✓ 投稿成功")
        else:
            print(f"✗ エラー: {response.text}")

    return xmltodict.parse(response.text)["entry"]  # 辞書型で出力


if __name__ == "__main__":
    if DEBUG:
        entry_xml = xml_unparser("タイトル", "本文のテスト")
        data = uploader(entry_xml)  # 辞書型

        print(
            f"投稿に成功しました。\nタイトル：{data["title"]}\n著者：{data["author"]["name"]}\n{"-" * 15}本文{"-" * 15}\n{data["content"]["#text"]}"
        )
