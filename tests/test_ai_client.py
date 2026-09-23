import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

from cha2hatena.llm.conversational_ai import AiOutput, LlmConfig
from cha2hatena.llm.gemini_client import GeminiClient
from cha2hatena.llm.llm_stats import TokenStats


def _llm_config(model: str = "gemini-2.5-flash") -> LlmConfig:
    return LlmConfig(
        prompt="ブログ用に要約してください。",
        model=model,
        temperature=0.7,
        api_key="test-api-key",
        conversation="user: hello\nassistant: hi",
    )


def test_gemini_client_get_summary_uses_mocked_google_sdk(monkeypatch):
    response = SimpleNamespace(
        text='{"title": "Test Title", "content": "Test Content", "categories": ["Python", "Test"]}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=10,
            thoughts_token_count=2,
            candidates_token_count=5,
        ),
    )
    generate_content = MagicMock(return_value=response)
    models = SimpleNamespace(generate_content=generate_content)
    client_class = MagicMock(return_value=SimpleNamespace(models=models))
    generate_content_config = MagicMock(return_value={"config": "sentinel"})

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    types_module = ModuleType("google.genai.types")
    errors_module = ModuleType("google.genai.errors")

    class ClientError(Exception):
        pass

    class ServerError(Exception):
        pass

    genai_module.Client = client_class
    genai_module.types = types_module
    types_module.GenerateContentConfig = generate_content_config
    errors_module.ClientError = ClientError
    errors_module.ServerError = ServerError
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", errors_module)

    ai_client = GeminiClient(_llm_config())

    result, stats = ai_client.get_summary()

    assert result == {
        "title": "Test Title",
        "content": "Test Content",
        "categories": ["Python", "Test"],
    }
    assert isinstance(stats, TokenStats)
    assert stats.input_tokens == 10
    assert stats.thoughts_tokens == 2
    assert stats.output_tokens == 5

    client_class.assert_called_once_with(api_key="test-api-key")
    generate_content_config.assert_called_once_with(
        temperature=0.7,
        response_mime_type="application/json",
        response_json_schema=AiOutput.model_json_schema(),
    )
    generate_content.assert_called_once_with(
        model="gemini-2.5-flash",
        contents="ブログ用に要約してください。\n\nuser: hello\nassistant: hi",
        config={"config": "sentinel"},
    )
