import logging
import pytest

from cha2hatena.llm.conversational_ai import ConversationalAi, LlmConfig
from cha2hatena.llm import gemini_client
from cha2hatena.llm.llm_stats import TokenStats


logger = logging.getLogger()


@pytest.fixture
def mock_GeminiClient(monkeypatch):
    class _mock_Gemini(ConversationalAi):
        def get_summary(self) -> tuple[dict, TokenStats]:
            print("*" * 100)
            print("mockテスト: get_summary")
            print("*" * 100)

            data = {
                "title": "テスト実行中",
                "content": "これはget_summaryのモックです",
                "categories": ["カテゴリ1", "カテゴリー2", "カテゴリー3"],
            }

            stats = TokenStats(
                input_tokens=1000,
                thoughts_tokens=1500,
                output_tokens=2000,
                input_letter_count=len(self.prompt),
                output_letter_count=500,
                model=self.model,
            )

            return data, stats

    monkeypatch.setattr(gemini_client, "GeminiClient", _mock_Gemini)
    return _mock_Gemini


@pytest.fixture
def mock_create_ai_client(monkeypatch):
    def _mock_create(config: LlmConfig):
        config.model = "gemini-2.5-flash"
        client = gemini_client.GeminiClient(config)
        return client

    monkeypatch.setattr("cha2hatena.main.create_ai_client", _mock_create)
    return _mock_create
