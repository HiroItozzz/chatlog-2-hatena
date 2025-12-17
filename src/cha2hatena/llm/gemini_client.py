import logging

from .conversational_ai import BlogPost, ConversationalAi
from .llm_stats import TokenStats

logger = logging.getLogger(__name__)


class GeminiClient(ConversationalAi):
    def get_summary(self):
        from google import genai
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        logger.warning("Geminiからの応答を待っています。")
        logger.debug(f"APIリクエスト中。APIキー: ...{self.api_key[-5:]}")

        # api_key引数なしでも、環境変数"GEMNI_API_KEY"の値を勝手に参照するが、可読性のため代入
        client = genai.Client(api_key=self.api_key)

        max_retries = 3
        for i in range(max_retries):
            # generate_contentメソッドは内部的にHTTPレスポンスコード200以外の場合は例外を発生させる
            try:
                response = client.models.generate_content(  # リクエスト
                    model=self.model,
                    contents=self.prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json",  # 構造化出力
                        response_json_schema=BlogPost.model_json_schema(),
                    ),
                )
                print("Geminiによる要約を受け取りました。")
                break
            except ServerError:
                super().handle_server_error(i, max_retries)
            except ClientError as e:
                super().handle_client_error(e)
            except Exception as e:
                super().handle_unexpected_error(e)

        data = super().check_response(response.text)

        stats = TokenStats(
            response.usage_metadata.prompt_token_count,
            response.usage_metadata.thoughts_token_count,
            response.usage_metadata.candidates_token_count,
            len(self.prompt),
            len(response.text),
            self.model,
        )

        return data, stats
