from pathlib import Path

from cha2hatena import json_loader as jl

sample_paths = [
    Path(r"sample\ChatGPT-sample.json"),
    Path(r"sample\Claude-sample.json"),
]
ai_names = ["ChatGPT", "Claude"]


def test_json_loader():
    result = jl.json_loader(sample_paths, ai_names)
    with open("outputs/test_json_loader.txt", "w", encoding="utf-8") as f:
        f.write(result)

    assert isinstance(result, str)
    assert len(result) > 0


if __name__ == "__main__":
    a = jl.json_loader(sample_paths, ai_names)
    print(a[:200])
