import json
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
DEBUG = config["other"]["debug"].lower() in ("true", "1", "t")


def json_loader(path: Path) -> list:
    if DEBUG:
        print(f"Loading: {path}")

    AI_LIST = ["Claude", "Gemini", "ChatGPT"]

    ai_name = next((p for p in AI_LIST if path.name.startswith(p)), "Unknown AI")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        dates_meta = data["metadata"]["dates"]
    except KeyError as e:
        raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"エラー：ファイル形式を確認してください - {path.name}") from e

    meta_date_format = "%m/%d/%Y %H:%M:%S"  # メタデータとメッセージでフォーマットが違う
    created_datetime = datetime.strptime(
        (dates_meta.get("created")), meta_date_format  # start time
    )
    updated_datetime = datetime.strptime(
        (dates_meta.get("updated")), meta_date_format  # updated time
    )

    logs = []
    latest_datetime = created_datetime  # 初期化
    try:
        for message in data["messages"]:
            timestamp = message.get("time")
            text_datetime = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S")
            time_diff = text_datetime - latest_datetime

            # Skip messages from previous days unless more than an hour has passed
            if not DEBUG:
                if text_datetime.date() != latest_datetime.date():
                    if time_diff > timedelta(hours=1):
                        latest_datetime = text_datetime
                        continue

            if message.get("role") == "Prompt":
                agent = "You"
            elif message.get("role") == "Response":
                agent = ai_name
            else:
                agent = message.get("role")
                if DEBUG:
                    print(f"Detected agent other than You and {ai_name}: {agent}")

            text = message.get("say")
            logs.append(f"{timestamp} \nagent: {agent}\n {text} \n\n {'-' * 50}\n")
            latest_datetime = text_datetime

    except KeyError:
        raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e

    conversation = "\n".join(logs)

    if DEBUG:
        print(f"total_logs: {len(logs)}")
        print(f"{conversation[:200]}")
    return conversation
