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
                model=self.model
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



def __2_mock_summarize_and_upload(monkeypatch):
    def _mock_summarize_and_upload(
        preset_categories: list,
        llm_config: dict,
        hatena_secret_keys: dict,
        debug_mode: bool = False,
    ) -> tuple[dict, dict]:
        # GoogleへAPIリクエスト
        llm_outputs = {"title": "mock", "content": "mock", "categories": ["mock"]}
        llm_stats = TokenStats(
            input_tokens=10000,
            thoughts_tokens=1010,
            output_tokens=954,
            input_letter_count=8000,
            output_letter_count=1544,
            model="gemini-2.5-flash"
        )
        response_dict = {
            "status_code": 201,
            # Atom名前空間の要素
            "title": "タイトル",  # XML名前空間の実体
            "content": "内容はこちら",
            "link_edit_user": "URL_edit",
            "link_alternate": "URL_normal",
            "categories": ["cat1", "cat2"],
            # app名前空間の要素
            "is_draft": None,
        }
        return response_dict, llm_stats

    monkeypatch.setattr("cha2hatena.main.summarize_and_upload", _mock_summarize_and_upload)
    return _mock_summarize_and_upload
