import logging
from datetime import datetime
import pytest

from cha2hatena import hatenablog_poster
from cha2hatena.llm.gemini_client import GeminiClient
from cha2hatena.llm.deepseek_client import DeepseekClient
from cha2hatena.llm.utils import create_ai_client

logger = logging.getLogger()



def mock_get_summary(monkeypatch):
    def _gemini(
        conversation: str,
        api_key: str,
        model: str,
        temperature: float,
        prompt: str,
    ) -> tuple[dict, dict]:

        print("*" * 100)
        print("mockテスト: get_summary")
        print("*" * 100)

        data = {"title": "テスト実行中",
                "content":"これはget_summaryのモックです",
                "categories":["カテゴリ1","カテゴリー2","カテゴリー3"]}

        stats = {
            "output_letter_count": 500,
            "input_tokens": 1000,
            "thoughts_tokens": 1500,
            "output_tokens": 2000,
        }

        return data, stats
    
    monkeypatch.setattr("cha2hatena.ai_client.get_summary", _gemini)
    return _gemini

@pytest.fixture
def __mock_summarize_and_upload(monkeypatch):
    def _summarize_and_upload(
        preset_categories: list,
        llm_config: dict,
        hatena_secret_keys: dict,
        debug_mode: bool = False,
        ) -> tuple[dict, dict]:
        # GoogleへAPIリクエスト
        llm_outputs, llm_stats = create_ai_client(llm_config).get_summary()

        # はてなブログへ投稿 投稿結果を辞書型で返却
        response_dict = hatenablog_poster.blog_post(
            **llm_outputs,
            hatena_secret_keys=hatena_secret_keys,
            preset_categories=preset_categories,
            author=None,  # str | None   Noneの場合自分のはてなID
            updated=None,  # datetime | None  公開時刻設定。Noneの場合5分後に公開
            is_draft=debug_mode,  # デバッグ時は下書き
        )
        return response_dict, llm_stats
    monkeypatch.setattr("cha2hatena.main.summarize_and_upload", _summarize_and_upload)
    return _summarize_and_upload

@pytest.fixture
def __test_aiclient(monkeypatch):
    def create_ai_client(params):
        if params["model"].startswith("gemini"):
            client = GeminiClient(**params)
        elif params["model"].startswith("deepseek"):
            client = DeepseekClient(**params)
        else:
            logger.error("モデル名が正しくありません。実行を中止します。")
            logger.error(f"モデル名: {params['model']}")
        return client
    monkeypatch.setattr("cha2hatena.main.hinge", create_ai_client)
    return create_ai_client