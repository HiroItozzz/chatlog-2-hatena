import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv(override=True)
config_path = Path("config.yaml")
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "t")

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PROMPT = config["ai"]["prompt"]
MODEL = config["ai"]["model"]
LEVEL = config["ai"]["thoughts_level"]


class BlogParts(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(description="ブログの本文（マークダウン形式）")
    categories: List[str] = Field(description="カテゴリー一覧")
    author: Optional[str] = None
    updated: Optional[datetime] = None


class BlogParts(BaseModel):
    title: str = Field(description="ブログのタイトル。")
    content: str = Field(description="ブログの本文（マークダウン形式）")
    categories: List[str] = Field(description="カテゴリー一覧")
    author: Optional[str] = None
    updated: Optional[datetime] = None


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
    api_key: str,
    model: str = "gemini-2.5-pro",
    thoughts_level: int = -1,
    custom_prompt: str = "please summarize the following conversation for my personal blog article. Keep it under 200 words: ",
) -> tuple[BlogParts, dict]:

    if DEBUG:
        print(f"Gemini using API_KEY now: '...{api_key[-5:]}'")

    # The client gets the API key from the environment variable `GEMINI_API_KEY` automatically without attribution.
    client = genai.Client(api_key=api_key)

    # Turn off thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=0) for gemini-2.5-flash
    # Turn on dynamic thinking:
    # thinking_config=types.ThinkingConfig(thinking_budget=-1)
    max_retries = 3
    for i in range(max_retries):
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
                print(f"Server seems to be busy. Retry {5 * (i+1)} seconds later.")
                time.sleep(5 * (i + 1))  # 5秒、10秒、15秒と待つ
            else:
                raise

    contents = BlogParts.model_validate_json(response.text)

    message = (
        "static thinking"
        if thoughts_level == 0
        else (
            "dynamic thinking"
            if thoughts_level == -1
            else f"thoughts limit: {thoughts_level}"
        )
    )
    ### リファクタ予定 ###
    input_tokens = response.usage_metadata.prompt_token_count
    thoughts_tokens = response.usage_metadata.thoughts_token_count
    output_tokens = response.usage_metadata.candidates_token_count
    ####################

    stats = {
        "input_tokens": response.usage_metadata.prompt_token_count,
        "thoughts_tokens": response.usage_metadata.thoughts_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count,
    }

    if DEBUG:
        total_output_tokens = thoughts_tokens + output_tokens
        input_fee = Gemini_fee().calculate(
            model, token_type="input", tokens=input_tokens
        )
        thoughts_fee = Gemini_fee().calculate(model, "output", thoughts_tokens)
        output_fee = Gemini_fee().calculate(model, "output", output_tokens)
        total_output_fee = thoughts_fee + output_fee

        print(f"Got your summary from AI: {response.text[:100]}")
        print(
            f"Input tokens: {input_tokens},fee: {input_fee}\n \
              Thoughts tokens: {thoughts_tokens}, fee: {thoughts_fee}\n \
                Output_tokens: {output_tokens}, fee: {output_fee}\n \
              Total ouput tokens: {total_output_tokens}, fee: {total_output_fee}\n \
              Total fee: {input_fee + total_output_fee}\n \
                Thoughts level: {message} "
        )

    return contents, stats


def print_debug_info():
    """デバッグ部分を移行予定"""
    pass


if __name__ == "__main__":
    pass
