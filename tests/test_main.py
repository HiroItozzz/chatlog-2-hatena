import logging
import sys

from cha2hatena import main

logger = logging.getLogger(__name__)

def test_main(monkeypatch, mock_get_summary):
    argv = ["sample/Claude-sample.json", "sample/ChatGPT-sample.json"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("cha2hatena.ai_client.get_summary", mock_get_summary)
    main.main()
