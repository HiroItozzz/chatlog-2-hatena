"""会話ログ読み込みのテスト

読み込み層は今後クラス化・インターフェース化する予定のため、
内部ヘルパーではなく「ファイル → LLMに渡すテキスト」という入出力だけを検証する。
"""

import json
from pathlib import Path

import pytest

from cha2hatena import json_loader as jl

SAMPLE_DIR = Path(__file__).parent.parent / "sample"


def load(paths: list[Path]) -> str:
    loader = jl.ExtentionExporterLoader(paths)
    return loader.load()


def write_json(path: Path, messages: list[dict]) -> Path:
    path.write_text(json.dumps({"messages": messages}, ensure_ascii=False), encoding="utf-8")
    return path


def exporter_msg(role: str, time: str | None, say: str) -> dict:
    """Claude/ChatGPT/Gemini Exporter形式"""
    msg = {"role": role, "say": say}
    if time is not None:
        msg["time"] = time
    return msg


# --- サンプルファイル ---


@pytest.mark.parametrize("name", ["Claude-sample.json", "ChatGPT-sample.json"])
def test_sample_file_is_converted_to_text(name):
    result = load([SAMPLE_DIR / name])

    first_say = json.loads((SAMPLE_DIR / name).read_text(encoding="utf-8"))["messages"][0]["say"]
    assert first_say.splitlines()[0] in result
    assert "👤 User" in result


def test_multiple_files_are_joined_in_order():
    result = load([SAMPLE_DIR / "Claude-sample.json", SAMPLE_DIR / "ChatGPT-sample.json"])

    assert result.index("1個目の会話") < result.index("2個目の会話")
    assert "🤖 Claude" in result
    assert "🤖 ChatGPT" in result


# --- 話者判定 ---


def test_speaker_uses_ai_name_from_file_prefix(tmp_path):
    path = write_json(
        tmp_path / "Gemini-foo.json",
        [exporter_msg("Prompt", None, "質問"), exporter_msg("Response", None, "回答")],
    )
    result = load([path])

    assert "👤 User" in result
    assert "🤖 Gemini" in result


def test_unknown_prefix_falls_back_to_unknown_ai(tmp_path):
    path = write_json(tmp_path / "foo.json", [exporter_msg("Response", None, "回答")])

    assert "🤖 Unknown_AI" in load([path])


# --- その日の会話だけを抽出 ---


def test_messages_are_in_chronological_order(tmp_path):
    path = write_json(
        tmp_path / "Claude-x.json",
        [
            exporter_msg("Prompt", "2025/11/20 10:00:00", "最初"),
            exporter_msg("Response", "2025/11/20 10:01:00", "二番目"),
            exporter_msg("Prompt", "2025/11/20 10:02:00", "最後"),
        ],
    )
    result = load([path])

    assert result.index("最初") < result.index("二番目") < result.index("最後")


def test_previous_day_after_long_gap_is_excluded(tmp_path):
    path = write_json(
        tmp_path / "Claude-x.json",
        [
            exporter_msg("Prompt", "2025/11/19 10:00:00", "前日の話"),
            exporter_msg("Prompt", "2025/11/20 10:00:00", "今日の話1"),
            exporter_msg("Response", "2025/11/20 10:05:00", "今日の話2"),
        ],
    )
    result = load([path])

    assert "今日の話1" in result
    assert "今日の話2" in result
    assert "前日の話" not in result


def test_conversation_continuing_past_midnight_is_kept(tmp_path):
    path = write_json(
        tmp_path / "Claude-x.json",
        [
            exporter_msg("Prompt", "2025/11/19 23:30:00", "日付をまたぐ前"),
            exporter_msg("Response", "2025/11/20 00:30:00", "日付をまたいだ後"),
        ],
    )
    result = load([path])

    assert "日付をまたぐ前" in result
    assert "日付をまたいだ後" in result


def test_all_messages_are_kept_without_timestamps(tmp_path):
    path = write_json(
        tmp_path / "ChatGPT-x.json",
        [exporter_msg("Prompt", None, "古い話"), exporter_msg("Response", None, "新しい話")],
    )
    result = load([path])

    assert "古い話" in result
    assert "新しい話" in result


def test_claude_conversation_extractor_format(tmp_path):
    path = write_json(
        tmp_path / "Claude-code.json",
        [
            {"role": "user", "timestamp": "2025-11-19T10:00:00.000Z", "content": "前日の話"},
            {"role": "user", "timestamp": "2025-11-20T10:00:00.000Z", "content": "質問"},
            {"role": "assistant", "timestamp": "2025-11-20T10:01:00.000Z", "content": "回答"},
        ],
    )
    result = load([path])

    assert "質問" in result
    assert "回答" in result
    assert "前日の話" not in result
    assert "🤖 Claude" in result


# --- テキスト入力 ---


@pytest.mark.parametrize("suffix", [".txt", ".md"])
def test_text_file_is_passed_through(tmp_path, suffix):
    path = tmp_path / f"memo{suffix}"
    path.write_text("そのまま渡される本文", encoding="utf-8")

    assert "そのまま渡される本文" in load([path])


# --- エラー ---


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("a,b", encoding="utf-8")

    with pytest.raises(ValueError):
        load([path])


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "Claude-broken.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError):
        load([path])


def test_json_without_messages_raises(tmp_path):
    path = tmp_path / "Claude-empty.json"
    path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")

    with pytest.raises(KeyError):
        load([path])
