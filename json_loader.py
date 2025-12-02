import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def json_loader(path: Path, ai_name) -> str:

    logger.info(f"ファイルを読み込みます: {path.name}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        messages = data["messages"]
    except KeyError as e:
        raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"エラー：ファイル形式を確認してください - {path.name}") from e

    dt_format = "%Y/%m/%d %H:%M:%S"
    latest = messages[-1].get("time", "")
    latest_dt = datetime.strptime(latest, dt_format) if latest else None
    # 初期化
    previous_dt = latest_dt

    logs = []
    logger.info(f"{len(messages)}件のメッセージを処理中...")

    try:
        for message in reversed(messages):  # 逆順
            timestamp = message.get("time", "")

            # 当日のメッセージではないかつ3時間以上時間が空いた場合ループを抜ける
            if timestamp:
                msg_dt = datetime.strptime(timestamp, dt_format)
                if msg_dt.date() != latest_dt.date():
                    if previous_dt - msg_dt > timedelta(hours=3):
                        break

            if message.get("role") == "Prompt":
                agent = "You"
            elif message.get("role") == "Response":
                agent = ai_name
            else:
                agent = message.get("role")
                logger.debug(
                    f"{'='*25}Detected agent other than You and {ai_name}: {agent} {'='*25}"
                )

            text = message.get("say")
            logs.append(
                f"{timestamp} \nagent: {agent}\n[message]\n{text} \n\n {'-' * 50}\n"
            )

            if timestamp:
                previous_dt = msg_dt

        if timestamp is None:
            print("会話履歴に時刻情報がありません。すべての会話を取得します。")

    except KeyError as e:
        raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e

    conversation = "\n".join(logs[::-1])  # 順番を戻す

    logger.info(f"{len(logs)}件の発言を取得しました。")
    print(f"{'='*25}最初のメッセージ{'='*25}\n{logs[0][:100]}")
    print(f"{'='*25}最後のメッセージ{'='*25}\n{logs[-1][:100]}")
    print("=" * 60)
    print("☑ jsonをテキストに変換しました。\n")

    return conversation
