import logging
import os
import sys

import requests

logger = logging.getLogger(__name__)


def line_messenger(content: int, line_access_token):

    URL = "https://api.line.me/v2/bot/message/broadcast"

    logging.debug(len(line_access_token), line_access_token[-5:])

    if line_access_token:
        logger.debug("アクセストークンを取得")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer <{line_access_token}>",
    }

    message = {
        "type": "text",
        "text": content,
    }
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
