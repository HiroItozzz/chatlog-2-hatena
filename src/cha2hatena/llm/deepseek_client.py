import logging
import sys

from .conversational_ai import BlogPost, ConversationalAi, TokenStats

logger = logging.getLogger(__name__)


class DeepseekClient(ConversationalAi):
    def get_summary(self) -> tuple[dict, TokenStats]:
        from openai import OpenAI

        statement = f"次の行から示すプロンプトはこのPydanticモデルに合うJSONで出力してください: {BlogPost.model_json_schema()}\n"
        self.prompt = statement + self.prompt

        logger.warning("Deepseekからの応答を待っています。")
        logger.debug(f"APIリクエスト中。APIキー: ...{self.api_key[-5:]}")

        client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

        max_retries = 3
        for i in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": self.prompt}],
                    response_format={"type": "json_object"},
                    stream=False,
                )
                break
            except Exception as e:
                # https://api-docs.deepseek.com/quick_start/error_codes
                if any(code in str(e) for code in [500, 502, 503]):
                    super().handle_server_error(i, max_retries)
                elif "429" in str(e):
                    logger.error("APIレート制限。しばらく経ってから再実行してください。")
                    raise
                elif "401" in str(e):
                    logger.error("エラー：APIキーが誤っているか、入力されていません。")
                    logger.error(f"実行を中止します。詳細：{e}")
                    sys.exit(1)
                elif "402" in str(e):
                    logger.error("残高が不足しているようです。アカウントを確認してください。")
                    logger.error(f"実行を中止します。詳細：{e}")
                    sys.exit(1)
                elif "422" in str(e):
                    logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
                    logger.error(f"実行を中止します。詳細：{e}")
                    sys.exit(1)
                else:
                    super().handle_unexpected_error(e)

        generated_text = response.choices[0].message.content
        data = super().check_response(generated_text)

        stats = TokenStats(
            response.usage.prompt_tokens,
            getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0),
            response.usage.completion_tokens,
            len(self.prompt),
            len(generated_text),
            self.model,
        )

        return data, stats
