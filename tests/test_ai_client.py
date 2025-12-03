import os
from pathlib import Path

from ch2hatena.ai_client import GeminiStructure, get_summary
from dotenv import load_dotenv

load_dotenv()


def test_ai_client():
    API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    path = Path(r"sample/conversation.txt")
    text = path.read_text(encoding="utf-8")
    costom_prompt = "please summarize the following conversation for my personal blog article. Keep it under 200 words in Japanese: "
    model = "gemini-2.5-flash"

    gemini_config = {
        "conversation": text,
        "gemini_api_key": API_KEY,
        "custom_prompt": costom_prompt,
        "model": model,
        "thoughts_level": -1,
    }

    result, stats = get_summary(**gemini_config)  # -> GeminiStructure, dict[int]
    print("=====タイトル:", result.title)
    print(f"=====内容：{len(result.content)}文字/n", result.content[:50])
    print("=====カテゴリー", " ".join(result.categories))
    print(
        f"stats：{stats['input_tokens']}, {stats['thoughts_tokens']}, {stats['output_tokens']}"
    )
    assert len(result.content) > 0
    assert stats["input_tokens"] > 0
    assert len(result.categories) > 1
