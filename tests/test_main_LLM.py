import logging
import sys

from cha2hatena import main

logger = logging.getLogger(__name__)

def test_main(monkeypatch, __mock_summarize_and_upload,):
    argv = ["sample/Claude-sample.json", "sample/ChatGPT-sample.json"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("cha2hatena.main.summarize_and_upload",__mock_summarize_and_upload)
    main.main()
