import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

REQUEST_TOKEN_URL = "https://www.hatena.com/oauth/initiate"
BASE_URL = "https://www.hatena.ne.jp/oauth/authorize"


load_dotenv()
CONSUMER_KEY = os.getenv("HATENA_CONSUMER_KEY", "").strip()
CONSUMER_SECRET = os.getenv("HATENA_CONSUMER_SECRET", "").strip()


# OAuth認証のためにHTTPリクエストの引数をOAuth指定の形式に整形
oauth = OAuth1Session(
    CONSUMER_KEY, client_secret=CONSUMER_SECRET, callback_uri="oob"
)  # callback_uriはリダイレクト先を指定する引数。"oob"はそれが存在しないことを表す（"Out of Band）。自作アプリの場合必須


# 管理者用キーを使用し個別ユーザー初回認証用のキーのペアを取得
response = oauth.fetch_request_token(
    REQUEST_TOKEN_URL,
    params={"scope": "write_public,read_public,write_private,read_private"},
)  # はてなの場合scope引数で権限の指定が必要。この場合全権限

# これは初回限定
resource_owner_key = response.get("oauth_token")
resource_owner_secret = response.get("oauth_token_secret")


# 人間の手によるOAuth認証
authorization_url = oauth.authorization_url(BASE_URL)
print(
    f"Please go here and authorize, {authorization_url}"
)  # リダイレクトに相当する箇所

verifier = input(
    "Please input oauth_verifier here:"
)  # 画面に表示されたコードを入力し自分のアカウントへのアクセスを許可する


ACCESS_TOKEN_URL = "https://www.hatena.com/oauth/token"

# 管理者用キー、初回認証用キー、を反映し再度HTTPリクエストの引数を指定の形式に整形
oauth = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)

# 個別ユーザー用キーを取得。
response = oauth.fetch_access_token(ACCESS_TOKEN_URL)
access_token = response.get("oauth_token")
access_token_secret = response.get("oauth_token_secret")

# この2つは今後ずっと使う
print(f"Access Token: {access_token}")
print(f"Access Token Secret: {access_token_secret}")
