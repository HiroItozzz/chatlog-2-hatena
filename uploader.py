import os
import xml.etree.ElementTree as E
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session


load_dotenv(override=True)

# 環境変数を読み込み
CONSUMER_KEY = os.getenv("HATENA_CONSUMER_KEY", None).strip()
CONSUMER_SECRET = os.getenv("HATENA_CONSUMER_SECRET", None).strip()
ACCESS_TOKEN = os.getenv("HATENA_ACCESS_TOKEN", None).strip()
ACCESS_TOKEN_SECRET = os.getenv("HATENA_ACCESS_TOKEN_SECRET", None).strip()

URL = os.getenv(
    "HATENA_BASE_URL", None
).strip()  # https://blog.hatena.ne.jp/{はてなID}/{ブログID}/atom/


entry_xml = r"""<?xml version="1.0" encoding="utf-8"?>

<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>初めての投稿</title>
  <author><name>name</name></author>
  <content type="text/plain">
    pythonでOAuth認証を行いAPIで送信し投稿しています。これからプログラミングの学習記録を自動投稿していく予定。
  </content>
  <category term="Scala" />
  <app:control>
    <app:draft>yes</app:draft>
    <app:preview>no</app:preview>
  </app:control>
</entry>"""


oauth = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=ACCESS_TOKEN,
    resource_owner_secret=ACCESS_TOKEN_SECRET,
)
response = oauth.post(
    URL, data=entry_xml, headers={"Content-Type": "application/xml; charset=utf-8"}
)
