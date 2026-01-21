import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from .llm_stats import TokenStats

logger = logging.getLogger(__name__)


class LlmConfig(BaseModel):
    prompt: str = Field(min_length=1, description="AIに送るプロンプト")
    model: str = Field(pattern=r"^(gemini|deepseek)-.+", default="gemini-2.5-flash", description="使用するLLMモデル")
    temperature: float = Field(ge=0, le=2.0, default=1.1, description="生成時の温度パラメータ")
    api_key: str = Field(min_length=1, description="API キー")
    conversation: str = Field(description="会話ログ")


# llm_outputs, llm_stats = hinge(llm_config)
# llm_outputs = {title: , content: , categories:}
# llm_stats = {input_tokens:, thoughts_tokens:, output_tokens:}


class AiOutput(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(description="ブログの本文（マークダウン形式）。")
    categories: List[str] = Field(description="カテゴリー一覧", max_length=4)


class ConversationalAi(ABC):
    def __init__(self, config: LlmConfig):
        self.model = config.model
        self.api_key = config.api_key
        self.temperature = config.temperature
        self.company_name = "Google" if self.model.startswith("gemini") else "Deepseek"
        STATEMENT = (
            f"またその最後には、「この記事は {self.model} により自動生成されています」と目立つように注記してください。"
        )
        self.prompt = config.prompt + STATEMENT + "\n\n" + config.conversation

    @abstractmethod
    def get_summary(self) -> tuple[dict, TokenStats]:
        pass

    def handle_server_error(self, i, max_retries):
        if i < max_retries - 1:
            logger.warning(f"{self.company_name}の計算資源が逼迫しているようです。{5 * (i + 1)}秒後にリトライします。")
            time.sleep(5 * (i + 1))
        else:
            logger.warning(f"{self.company_name}は現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.warning("実行を中止します。")
            sys.exit(1)

    def handle_client_error(self, e: Exception):
        logger.error("エラー：APIレート制限。")
        logger.error("詳細はapp.logを確認してください。実行を中止します。")
        logger.info(f"詳細: {e}")
        sys.exit(1)

    def handle_unexpected_error(self, e: Exception):
        logger.error("要約取得中に予期せぬエラー発生。詳細はapp.logを確認してください。")
        logger.error("実行を中止します。")
        logger.info(f"詳細: {e}")
        raise

    def check_response(self, response_text):
        required_keys = {"title", "content", "categories"}
        try:
            data = json.loads(response_text)
            if set(data.keys()) == required_keys:
                logger.warning(f"{self.model}が構造化出力に成功")
        except Exception:
            logger.error(f"{self.model}が構造化出力に失敗。")
            output_path = Path.cwd() / "outputs"
            output_path.mkdir(exist_ok=True)
            file_path = output_path / "__summary.txt"
            file_path.write_text(response_text, encoding="utf-8")

            logger.error(f"{file_path}へ出力を保存しました。")
            sys.exit(1)

        return data
