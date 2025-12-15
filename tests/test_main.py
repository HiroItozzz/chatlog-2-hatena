import logging
import sys

from cha2hatena import main

logger = logging.getLogger(__name__)


def test_main(
    monkeypatch,
    mock_GeminiClient,
    mock_create_ai_client
):
    argv = ["sample/Claude-sample.json", "sample/ChatGPT-sample.json"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("cha2hatena.main.create_ai_client", mock_create_ai_client)
    monkeypatch.setattr("cha2hatena.main.gemini_client.GeminiClient", mock_GeminiClient)
    main.main()
