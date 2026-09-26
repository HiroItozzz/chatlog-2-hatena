import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


AI_NAMES = ["Claude", "Gemini", "ChatGPT", "Deepseek"]


class MessageLoader(ABC):
    @abstractmethod
    def load(self) -> str:...

    @property
    @abstractmethod
    def ai_name(self) -> str: ...

    @property
    @abstractmethod
    def conversation_title(self) -> str: ...


class ExtentionExporterLoader(MessageLoader):
    def __init__(self, paths: list[Path]):
        self.paths = paths
        # AI名とタイトルはファイル名だけで決まるので、ここで1回だけ判定しておく
        self._ai_names = [self._detect_ai_name(path) for path in paths]
        total = len(paths)
        self._titles = [
            self._make_title(path, ai_name, idx, total)
            for idx, (path, ai_name) in enumerate(zip(paths, self._ai_names), 1)
        ]

    @property
    def ai_name(self) -> str:
        return " ".join(self._ai_names)

    @property
    def conversation_title(self) -> str:
        return " ".join(self._titles)

    def load(self) -> str:
        """複数のjsonファイルをstrに"""

        logger.warning(f"{len(self.paths)}個のjsonファイルの読み込みを開始します")

        conversations = []

        # ファイルごとのループ
        for idx, (path, ai_name) in enumerate(zip(self.paths, self._ai_names), 1):
            logger.warning(f"{idx}個目のファイルを読み込みます: {path.name}")

            if path.suffix == ".json":
                conversation = f"# {idx}個目の会話\n\n"
                conversation += self.parse_json(path, ai_name)

            elif path.suffix in [".txt", ".md"]:
                conversation = f"{'=' * 20} {idx}個目の会話 {'=' * 20}\n\n"
                conversation += path.read_text(encoding="utf-8")

            else:
                raise ValueError(f"エラー：対応していないファイル形式です - {path.name}")

            conversations.append(conversation)

        logger.warning(f"☑ {len(self.paths)}件のjsonファイルをテキストに変換しました。\n")

        return "\n\n\n".join(conversations)

    def parse_json(self, path: Path, ai_name) -> str:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            messages = data["messages"]
        except KeyError as e:
            raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"エラー：ファイル形式を確認してください - {path.name}") from e

        # 会話の抽出→文字列へ
        try:
            logs, timestamp = self.convert_to_str(messages, ai_name)
        except KeyError as e:
            raise KeyError(f"エラー： jsonファイルの構成を確認してください - {path}") from e

        if timestamp is None:
            print(f"{path.name}の会話履歴に時刻情報がありません。すべての会話を取得しました。")

        conversation = "\n".join(logs)

        logger.warning(f"{len(logs) - 1}件の発言を取得: {path.name}")
        print(f"{'=' * 25}最初のメッセージ{'=' * 25}\n{conversation[:100]}")
        print(f"{'=' * 25}最後のメッセージ{'=' * 25}\n{conversation[-100:]}")
        print("=" * 60)

        return conversation

    def convert_to_str(self, messages: dict, ai_name: str) -> tuple[list, datetime | None]:
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

            agent = self._get_agent(message, ai_name)

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
        return logs[::-1], timestamp  # 順番を戻す

    @staticmethod
    def _detect_ai_name(path: Path) -> str:
        """ファイル名の接頭辞（<AI名>-）からAIの名前を判定"""
        return next(
            (ai for ai in AI_NAMES if path.stem.lower().startswith(ai.lower() + "-")),
            "Unknown_AI",
        )

    @staticmethod
    def _make_title(path: Path, ai_name: str, idx: int, total: int) -> str:
        """ファイル名からcsv出力用タイトルを作成（複数ファイルのときは番号付きで10文字に切る）"""
        if ai_name == "Unknown_AI":
            return path.stem
        title = path.stem[len(ai_name) + 1 :]
        return f"[{idx}]{title[:10]}" if total >= 2 else title

    def _get_agent(self, message: dict, ai_name: str) -> str:
        """話者判定・Gemini出力の精度向上のため"""
        if message.get("role") in ["Prompt", "user"]:
            agent = "👤 User"
        elif message.get("role") in ["Response", "assistant"]:
            agent = "🤖 " + ai_name
        else:
            agent = message.get("role", "")
            logger.debug(f"{'=' * 25}Detected agent other than You and {ai_name}: {agent} {'=' * 25}")
        return agent
