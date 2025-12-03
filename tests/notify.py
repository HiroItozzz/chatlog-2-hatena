import logging
import os
import sys

import requests

logger = logging.getLogger(__name__)


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

URL = "https://api.line.me/v2/bot/message/broadcast"

LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
print(len(LINE_ACCESS_TOKEN), LINE_ACCESS_TOKEN[:-5])

if LINE_ACCESS_TOKEN:
    logger.info("アクセストークンを取得")

import requests

# 辞書としてヘッダーを設定
headers = {
    # 送信するデータの形式を指定（例：JSON）
    "Content-Type": "application/json",
    # 認証トークンを含める（例：Bearer認証）
    "Authorization": f"Bearer <{LINE_ACCESS_TOKEN}>",
}

message = {"type": "text", "text": "✔ 初めてのライン通知です。届いてくれて嬉しいです。"}
body = {"messages": [message]}

res = requests.post(URL, headers=headers, json=body)

if res.status_code == 200:
    logger.debug("✓ LINE通知に成功しました。")
else:
    logger.info("LINE通知出来ませんでした。")
    logger.info(f"ステータスコード：{res.status_code}")
    res_dict = res.json()
    try:
        logger.info(f"詳細: {res_dict["message"]}")
        logger.info(f"{res_dict["details"][0]["message"]}")
    except Exception:
        logger.info("レスポンスを解析できませんでした。", exc_info=True)
