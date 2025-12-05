import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session


"""https://developer.hatena.ne.jp/ja/documents/auth/apis/oauth/consumer
    OAuth認証を行い他のアプリケーションにアカウントの操作権限を付与する操作
    上記URLの手順に従いCONSUMER_KEYとCONSUMER_SECRETを取得"""


REQUEST_TOKEN_URL = "https://www.hatena.com/oauth/initiate"
BASE_URL = "https://www.hatena.ne.jp/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.hatena.com/oauth/token"

load_dotenv()
CONSUMER_KEY = os.getenv("HATENA_CONSUMER_KEY", "").strip()
CONSUMER_SECRET = os.getenv("HATENA_CONSUMER_SECRET", "").strip()


# callback_uriはリダイレクト先を指定する引数：
# "oob"はそれが存在しないことを表す（"Out of Band"）。自作アプリの場合必要
oauth = OAuth1Session(
    client_key=CONSUMER_KEY, client_secret=CONSUMER_SECRET, callback_uri="oob"
)

# 一時認証用のキーのペアを取得
# scope引数で投稿のための権限を指定
response = oauth.fetch_request_token(
    REQUEST_TOKEN_URL,
    params={"scope": "write_public,read_public,write_private,read_private"},
)

# 一時的なキーを取得
resource_owner_key = response.get("oauth_token")
resource_owner_secret = response.get("oauth_token_secret")

# リダイレクト
authorization_url = oauth.authorization_url(BASE_URL)
print(f"次のURLへアクセスし認証用キーを取得してください: {authorization_url}")
verifier = input("取得した認証用キーを入力してください: ")

# すべてのキーを反映し再度リクエスト
oauth = OAuth1Session(
    client_key=CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)

# OAキーを取得。
response = oauth.fetch_access_token(ACCESS_TOKEN_URL)
access_token = response.get("oauth_token")
access_token_secret = response.get("oauth_token_secret")

print("以下のアクセストークンを保存し、.envへ入力してください:")
print(f"Access Token: {access_token}")
print(f"Access Token Secret: {access_token_secret}")
