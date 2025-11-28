import os
from pathlib import Path
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")


### 自動取得に変更予定 ###
INPUT_DIR = ""

INPUT_PATH = Path(
    r"E:\Dev\Projects\chatbot-logger\sample\Claude-Git LF!CRLF line ending issues across platforms (1).json"
)
####################


def json_formatter(raw_data: str, ai_name: str) -> list:
    logs = []

    data = json.loads(raw_data)

    dates_meta = data["metadata"]["dates"]
    format_meta = "%m/%d/%Y %H:%M:%S"

    created_datetime = datetime.strptime(
        (dates_meta.get("created")), format_meta
    )  # start time of the chat
    updated_datetime = datetime.strptime(
        (dates_meta.get("updated")), format_meta
    )  # updated time of the chat

    latest_datetime = created_datetime

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

    return logs


if __name__ == "__main__":
    with open(INPUT_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)

    output_texts = "\n".join(json_formatter(raw_data))

    output_dir = Path(os.getenv("OUTPUT_DIR").strip())
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / (INPUT_PATH.stem + ".txt")

    output_path.write_text(output_texts, encoding="utf-8")

    if DEBUG:
        print(f"output_text loaded!!: {output_texts[:50]}")
        exit()
