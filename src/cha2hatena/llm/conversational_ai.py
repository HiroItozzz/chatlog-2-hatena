import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

'''
LLM_CONFIG = {
    "prompt": config["ai"]["prompt"],
    "model": config["ai"]["model"],
    "temperature": config["ai"]["temperature"],
    "api_key": SECRET_KEYS.pop("GEMINI_API_KEY"),
    "conversation" : conversation
}
'''
# llm_outputs, llm_stats = hinge(llm_config)
# llm_outputs = {title: , content: , categories:}
# llm_stats = {input_tokens:, thoughts_tokens:, output_tokens:}

class BlogPost(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(
        description="ブログの本文（マークダウン形式）。"
    )
    categories: List[str] = Field(description="カテゴリー一覧", max_length=4)


class ConversationalAi(ABC):
    def __init__(self, model:str, api_key:str, conversation:str, prompt: str,temperature:float = 1.1):
        self.model = model or "gemini-2.5-flash"
        self.api_key = api_key
        self.temperature = temperature        
        self.company_name = "Google" if self.model.startswith("gemini") else "Deepseek"
        STATEMENT = f"またその最後には、「この記事は {self.model} により自動生成されています」と目立つように注記してください。"    
        self.prompt = prompt + STATEMENT+ "\n\n" + conversation

    @abstractmethod
    def get_summary(self) -> tuple[dict, dict]:
        pass

    def handle_server_error(self, i, max_retries):
        if i < max_retries - 1:
            logger.warning(
                f"{self.company_name}の計算資源が逼迫しているようです。{5 * (i + 1)}秒後にリトライします。"
            )
            time.sleep(5 * (i + 1))
        else:
            logger.warning(f"{self.company_name}は現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.warning("実行を中止します。")
            sys.exit(1)

    def handle_client_error(self, e:Exception):
        logger.error("エラー：APIレート制限。")
        logger.error("詳細はapp.logを確認してください。実行を中止します。")
        logger.info(f"詳細: {e}")
        sys.exit(1)

    def handle_unexpected_error(self, e:Exception):
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
    