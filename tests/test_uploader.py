from pathlib import Path
from pprint import pprint

import yaml
from dotenv import load_dotenv
from uploader import hatena_uploader, xml_unparser

load_dotenv(override=True)
config_path = Path("config.yaml")
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))


def test_hatena_uploader():

    # sample XML
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

    result = hatena_uploader(entry_xml)
    print(result)
    assert result
    assert len(result.keys())
