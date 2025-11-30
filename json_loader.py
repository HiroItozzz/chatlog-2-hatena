import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "t")


def json_loader(path: Path) -> str:
    if DEBUG:
        print(f"Loading: {path}")

    AI_LIST = ["Claude", "Gemini", "ChatGPT"]
    ai_name = next((p for p in AI_LIST if path.name.startswith(p)), "Unknown AI")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        dates_meta = data["metadata"]["dates"]
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

    if DEBUG:
        print(f"処理前： {len(messages)}行")

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
                if DEBUG:
                    print(f"Detected agent other than You and {ai_name}: {agent}")

            text = message.get("say")
            logs.append(
                f"{timestamp} \nagent: {agent}\n[message]\n{text} \n\n {'-' * 50}\n"
            )

            if timestamp:
                previous_dt = msg_dt

        if DEBUG:
            if timestamp is None:
                print("会話履歴にtimestampが見つかりませんでした。")

    except KeyError as e:
        raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e

    conversation = "\n".join(logs[::-1])  # 順番を戻す
    if DEBUG:
        print(f"処理後: {len(logs)}行")
        print(f"最初{"="*100}\n{logs[0][:100]}")
        print(f"最後{"="*100}\n{logs[-1][:100]}")

        output_path = Path("outputs/test_json_loader.txt")
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(conversation, encoding="utf-8")
        print(f"テストファイルを出力しました： {output_path}")

    return conversation
