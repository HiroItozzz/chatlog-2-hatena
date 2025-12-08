from pathlib import Path

from cha2hatena import json_loader as jl

sample_paths = [
    Path(r"sample\ChatGPT-sample.json"),
    Path(r"sample\Claude-sample.json"),
]
ai_names = ["ChatGPT", "Claude", "Gemini"]


def test_json_loader():
    result = jl.json_loader(sample_paths)
    output_dir = Path.cwd() / "outputs/"
    with open(output_dir / "test_json_loader.txt", "w", encoding="utf-8") as f:
        f.write(result)

    assert isinstance(result, str)
    assert len(result) > 0


if __name__ == "__main__":
    a = jl.json_loader(sample_paths)
    print(a[:200])
