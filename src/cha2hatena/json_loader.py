import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


### ユーティリティ関数
def ai_names_from_paths(paths: list[Path]) -> list:
    """AIの名前のリストを取得"""
    AI_LIST = ["Claude", "Gemini", "ChatGPT", "Deepseek"]
    ai_names = []
    for path in paths:
        ai_name = next(
            (ai for ai in AI_LIST if path.stem.lower().startswith(ai.lower() + "-")),
            "Unknown_AI",
        )
        ai_names.append(ai_name)
    return ai_names


def get_conversation_titles(paths: list[Path], ai_names: list) -> list:
    """インプットパスのリストをcsv出力用タイトルに処理"""
    titles = []
    for idx, (path, ai_name) in enumerate(zip(paths, ai_names), 1):
        if path.stem.startswith(ai_name + "-"):
            title = path.stem.replace(f"{ai_name}-", "", 1)
            title = f"[{idx}]{title[:10]}" if len(paths) >= 2 else title
            titles.append(title)
        else:
            titles.append(path.stem)
    return titles


def get_agent(message: dict, ai_name: str) -> str:
    """話者判定・Gemini出力の精度向上のため"""
    if message.get("role") in ["Prompt", "user"]:
        agent = "👤 User"
    elif message.get("role") in ["Response", "assistant"]:
        agent = "🤖 " + ai_name
    else:
        agent = message.get("role", "")
        logger.debug(f"{'=' * 25}Detected agent other than You and {ai_name}: {agent} {'=' * 25}")
    return agent


def convert_to_str(messages: dict, ai_name: str) -> tuple[list, datetime | None]:
    """jsonの本丸を処理"""

    logger.warning(f"{len(messages)}件のメッセージを処理中...")

    # 初期化
    latest_message = messages[-1]
    if "time" in latest_message:
        dt_format = "%Y/%m/%d %H:%M:%S"
        latest_dt_raw = latest_message.get("time")
    elif "timestamp" in latest_message:  # for Claude-Conversation-Extractor
        dt_format = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISOフォーマット
        latest_dt_raw = latest_message.get("timestamp")
    else:
        latest_dt_raw = None
    latest_dt = datetime.strptime(latest_dt_raw, dt_format) if latest_dt_raw else None
    logs = []
    previous_dt = latest_dt

    # 逆順
    for message in reversed(messages):
        # 時刻を取得（あれば）
        if "time" in message:
            timestamp = message.get("time")
        elif "timestamp" in message:  # for Claude-Conversation-Extractor
            timestamp = message.get("timestamp")
        else:
            timestamp = None

        # 当日のメッセージではないかつ3時間以上時間が空いた場合ループを抜ける
        if timestamp:
            msg_dt = datetime.strptime(timestamp, dt_format)
            if latest_dt is not None and msg_dt.date() != latest_dt.date():
                if previous_dt - msg_dt > timedelta(hours=3):
                    break

        agent = get_agent(message, ai_name)

        # メッセージを取得
        if "say" in message:
            text = message.get("say", "").replace("\n\n", "\n")
        elif "content" in message:  # for Claude-Conversation-Extractor
            text = message.get("content", "").replace("\n\n", "\n")
        else:
            raise KeyError

        logs.append(f"## agent: {agent} | date: {timestamp}  \nmessage:  \n{text}\n\n{'-' * 3}\n\n")

        if timestamp:
            previous_dt = msg_dt
    return logs, timestamp


def json_loader(paths: list[Path,]) -> str:
    """複数のjsonファイルをstrに"""

    logger.warning(f"{len(paths)}個のjsonファイルの読み込みを開始します")

    conversations = []
    ai_names = ai_names_from_paths(paths)

    # ファイルごとのループ
    for idx, (path, ai_name) in enumerate(zip(paths, ai_names), 1):
        logger.warning(f"{idx}個目のファイルを読み込みます: {path.name}")

        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                messages = data["messages"]
            except KeyError as e:
                raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e
            except json.JSONDecodeError as e:
                raise ValueError(f"エラー：ファイル形式を確認してください - {path.name}") from e

            # 会話の抽出→文字列へ
            try:
                logs, timestamp = convert_to_str(messages, ai_name)
            except KeyError as e:
                raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e

            if timestamp is None:
                print(f"{path.name}の会話履歴に時刻情報がありません。すべての会話を取得しました。")

            logs.append(f"# {idx}個目の会話\n\n")
            conversation = "\n".join(logs[::-1])  # 順番を戻す
            logger.warning(f"{len(logs) - 1}件の発言を取得: {path.name}")
            print(f"{'=' * 25}最初のメッセージ{'=' * 25}\n{logs[-2][:100]}")
            print(f"{'=' * 25}最後のメッセージ{'=' * 25}\n{logs[0][:100]}")
            print("=" * 60)

        elif path.suffix in [".txt", ".md"]:
            conversation = f"{'=' * 20} {idx}個目の会話 {'=' * 20}\n\n"
            conversation += path.read_text(encoding="utf-8")

        else:
            raise ValueError(f"エラー：対応していないファイル形式です - {path.name}")

        conversations.append(conversation)
        ai_names.append(ai_name)

    logger.warning(f"☑ {len(paths)}件のjsonファイルをテキストに変換しました。\n")

    return "\n\n\n".join(conversations)
