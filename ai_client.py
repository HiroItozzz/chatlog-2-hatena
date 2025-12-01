import logging
import time
from datetime import datetime
from typing import List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

logging.getLogger(__name__)


class BlogParts(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(
        description=f"ブログの本文（マークダウン形式）。その最後には、「この記事は Gemini により自動生成されています」と目立つように注記してください。"
    )
    categories: List[str] = Field(description="カテゴリー一覧", max_items=4)
    author: Optional[str]
    updated: Optional[datetime]


class Gemini_fee:
    def __init__(self):
        self.fees = {
            "gemini-2.5-flash": {"input": 0.03, "output": 2.5},  # $per 1M tokens
            "gemini-2.5-pro": {
                "under 0.2M": {"input": 1.25, "output": 10.00},
                "over 0.2M": {"input": 2.5, "output": 15},
            },
        }

    def calculate(self, model: str, token_type: str, tokens: int) -> float:
        if model == "gemini-2.5-pro":
            base_fees = self.fees["gemini-2.5-pro"]
            if tokens <= 200000:
                return tokens * base_fees["under 0.2M"][token_type] / 1000000
            else:
                return tokens * base_fees["over 0.2M"][token_type] / 1000000
        else:
            return tokens * self.fees[model][token_type] / 1000000


def get_summary(
    conversation: str,
    gemini_api_key: str,
    model: str = "gemini-2.5-pro",
    thoughts_level: int = -1,
    custom_prompt: str = "please summarize the following conversation for my personal blog article. Keep it under 200 words in Japanese: ",
) -> tuple[BlogParts, dict]:

    logging.info("Geminiからの応答を待っています。")
    logging.debug(f"APIキー: ...{gemini_api_key[-5:]}")

    # api_key引数なしの場合、環境変数"GEMNI_API_KEY"の値を勝手に読み込む
    client = genai.Client(api_key=gemini_api_key)

    max_retries = 3
    for i in range(max_retries):
        # generate_contentメソッドは内部的にHTTPレスポンスコード200以外の場合は例外を発生させる
        try:
            response = client.models.generate_content(  # リクエスト
                model=model,
                contents=f"{custom_prompt}\n\n{conversation}",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=thoughts_level
                    ),
                    response_mime_type="application/json",  # 構造化出力
                    response_json_schema=BlogParts.model_json_schema(),
                ),
            )
            break
        except Exception as e:
            if "503" in str(e) and i < max_retries - 1:
                logging.info(
                    f"Googleの計算資源が逼迫しているようです。{5 * (i+1)}秒後にリトライします。"
                )
                time.sleep(5 * (i + 1))  # 5秒、10秒、15秒と待つ
            else:
                logging.info(
                    f"Googleは現在過負荷のようです。少し時間をおいて再実行する必要があります。"
                )
                logging.debug(f"詳細：{e}", exc_info=True)
                logging.info(f"実行を終了します。")
                raise

    contents = BlogParts.model_validate_json(response.text)
    stats = {
        "output_letter_count": len(response.text),
        "input_tokens": response.usage_metadata.prompt_token_count,
        "thoughts_tokens": response.usage_metadata.thoughts_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count,
    }

    return contents, stats
