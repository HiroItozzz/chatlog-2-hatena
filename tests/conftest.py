import pytest


@pytest.fixture
def mock_get_summary(monkeypatch):
    def _gemini(
        conversation: str,
        gemini_api_key: str,
        model: str,
        thoughts_level: int,
        custom_prompt: str,
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
