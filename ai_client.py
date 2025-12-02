import logging
import time
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GeminiStructure(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(
        description=f"ブログの本文（マークダウン形式）。その最後には、「この記事は Gemini-2.5-pro により自動生成されています」と目立つように注記してください。"
    )
    categories: List[str] = Field(description="カテゴリー一覧", max_items=4)


class GeminiFee:
    def __init__(self):
        self.fees = {
            "gemini-2.5-flash": {"input": 0.03, "output": 2.5},  # $per 1M tokens
            "gemini-2.5-pro": {
                "under_0.2M": {"input": 1.25, "output": 10.00},
                "over_0.2M": {"input": 2.5, "output": 15.0},
            },
        }

    def calculate(self, model: str, token_type: str, tokens: int) -> float:
        if model == "gemini-2.5-pro":
            base_fees = self.fees["gemini-2.5-pro"]
            if tokens <= 200000:
                return tokens * base_fees["under_0.2M"][token_type] / 1000000
            else:
                return tokens * base_fees["over_0.2M"][token_type] / 1000000
        else:
            return tokens * self.fees[model][token_type] / 1000000


def get_summary(
    conversation: str,
    gemini_api_key: str,
    model: str = "gemini-2.5-pro",
    thoughts_level: int = -1,
    custom_prompt: str = "please summarize the following conversation for my personal blog article. Keep it under 200 words in Japanese: ",
) -> tuple[GeminiStructure, dict]:

    print("Geminiからの応答を待っています。")
    logger.debug(f"APIリクエスト中。APIキー: ...{gemini_api_key[-5:]}")

    # api_key引数なしでも、環境変数"GEMNI_API_KEY"の値を勝手に参照するが、可読性のため代入
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
                    response_json_schema=GeminiStructure.model_json_schema(),
                ),
            )
            break
        except Exception as e:
            if any(code in str(e) for code in ["500", "503"]) and i < max_retries - 1:
                logger.info(
                    f"Googleの計算資源が逼迫しているようです。{5 * (i+1)}秒後にリトライします。"
                )
                time.sleep(5 * (i + 1))  # 5秒、10秒、15秒と待つ
            else:
                logger.info(
                    f"Googleは現在過負荷のようです。少し時間をおいて再実行する必要があります。"
                )
                logger.debug(f"詳細：{e}", exc_info=True)
                logger.info(f"実行を中断します。")
                raise

    print("Geminiによる要約を受け取りました。")
    try:
        contents = GeminiStructure.model_validate_json(response.text)
        logger.debug("構造化出力のバリデーションに成功しました。")

    #### JSONパースによるエラーハンドリング実装予定
    except Exception as e:
        logger.info(
            "構造化出力のバリデーションに失敗しました。再度アプリを実行する必要があります。"
        )
        logger.info(f"詳細: {e}", exc_info=True)
        print("実行を中断します。")
        raise

    stats = {
        "output_letter_count": len(response.text),
        "input_tokens": response.usage_metadata.prompt_token_count,
        "thoughts_tokens": response.usage_metadata.thoughts_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count,
    }

    return contents, stats
