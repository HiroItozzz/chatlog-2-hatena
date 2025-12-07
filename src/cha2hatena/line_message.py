import logging

import requests

logger = logging.getLogger(__name__)


def line_messenger(content: str, line_access_token: str):
    URL = r"https://api.line.me/v2/bot/message/broadcast"

    logger.debug(f"LINEアクセストークン: ... {line_access_token[-5:]}")

    if line_access_token:
        logger.warning("アクセストークンを取得")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer <{line_access_token}>"}

    message = {"type": "text", "text": content}
    body = {"messages": [message]}

    res = requests.post(URL, headers=headers, json=body)

    if res.status_code == 200:
        logger.warning("✓ LINE通知に成功しました。")
    else:
        logger.error("LINE通知出来ませんでした。詳細は`app.log`を確認してください")
        logger.error(f"ステータスコード：{res.status_code}")
        try:
            res_dict = res.json()
            logger.info(f"詳細: {res_dict['message']}")
            logger.info(f"{res_dict['details'][0]['message']}")
        except Exception:
            logger.info("レスポンス内容を解析できませんでした。")
