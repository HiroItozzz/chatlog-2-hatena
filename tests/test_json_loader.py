from pathlib import Path

import json_loader as jl

sample_path = Path(r"E:\Dev\Projects\chatbot-logger\sample\ChatGPT-sample.json")


def test_json_loader():
    result = jl.json_loader(sample_path)
    assert isinstance(result, str)
    assert len(result) > 0


if __name__ == "__main__":
    a = jl.json_loader(sample_path)
    print(a[:200])
