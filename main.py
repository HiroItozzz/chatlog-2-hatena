import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import ai_client
import json_loader
import line_message
import pandas as pd
import uploader
import yfinance as yf
from dotenv import load_dotenv
from validate import initialize_config

logger = logging.getLogger(__name__)
load_dotenv(override=True)

# .envのDEBUG項目の存在と値でログレベル判定
try:
    DEBUG_ENV = os.environ.get("DEBUG", "False").lower() in ("true", "t", "1")
    initial_level = logging.DEBUG if DEBUG_ENV else logging.INFO
except Exception:
    DEBUG_ENV = False
    initial_level = logging.INFO

logging.basicConfig(
    level=initial_level,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def summarize_and_upload(
    preset_categories: list,
    gemini_config: dict,
    hatena_secret_keys: dict,
    debug_mode: bool = False,
) -> tuple[dict, dict]:

    # GoogleへAPIリクエスト
    gemini_structure, gemini_stats = ai_client.get_summary(**gemini_config)

    # はてなブログへ投稿
    xml_str = uploader.xml_unparser(
        gemini_structure,
        preset_categories=preset_categories,
        author=None,  # str | None   Noneの場合自分のはてなID
        updated=None,  # datetime | None  公開時刻設定。Noneの場合5分後に公開
        is_draft=debug_mode,  # デバッグ時は下書き
    )
    result = uploader.hatena_uploader(xml_str, hatena_secret_keys)  # 辞書型で返却

    return result, gemini_stats


def append_csv(path: Path, df: pd.DataFrame):
    """pathがなければ作成し、CSVに1行追記"""
    is_new_file = not path.exists()
    try:
        df.to_csv(
            path,
            encoding="utf-8-sig",
            index=False,
            mode="a",
            header=is_new_file,  # ファイルがなければヘッダー書き込み、あればFalse
        )
        if is_new_file:
            logger.info(f"新しいCSVファイルを作成しました: {path}")
        else:
            logger.info(f"CSVにデータを追記しました: {path.name}")
    except Exception:
        logger.exception("CSVファイルへの書き込み中にエラーが発生しました。")


def main(
    input_path: Path,
    preset_categories: list,
    gemini_config: dict,
    hatena_secret_keys: dict,
    debug_mode: bool = False,
):

    logger.debug("================================================")
    logger.debug(f"アプリケーションが起動しました。DEBUGモード: {debug_mode}")

    AI_LIST = ["Claude", "Gemini", "ChatGPT"]
    ai_name = next((p for p in AI_LIST if input_path.name.startswith(p)), "Unknown AI")

    conversation = json_loader.json_loader(input_path, ai_name)
    gemini_config["conversation"] = conversation

    # Googleで要約取得 & はてなへ投稿
    result, gemini_stats = summarize_and_upload(
        preset_categories, gemini_config, hatena_secret_keys, debug_mode=DEBUG
    )

    url = result.get("link_alternate", "")
    title = result.get("title", "")
    content = result.get("content", "")
    categories = result.get("categories", [])

    logger.info(f"はてなブログへの投稿に成功しました。")
    ###### 下書きの場合公開URLへのアクセス不能
    logger.info(f"URL: {url}")
    print("-" * 50)
    print(f"投稿タイトル：{title}")
    print(f"\n{'-' * 20}投稿本文{'-' * 20}")
    print(f"{content[:100]}")
    print("-" * 50)

    MODEL = gemini_config["model"]
    fee = ai_client.GeminiFee()
    i_fee = fee.calculate(MODEL, "input", gemini_stats["input_tokens"])
    th_fee = fee.calculate(MODEL, "output", gemini_stats["thoughts_tokens"])
    o_fee = fee.calculate(MODEL, "output", gemini_stats["output_tokens"])
    total_fee = i_fee + th_fee + o_fee

    # 為替レートを取得
    ticker = "USDJPY=X"
    try:
        dy_rate = yf.Ticker(ticker).history(period="1d").Close.iloc[0]
        total_JPY = total_fee * dy_rate
    except Exception as e:
        logging.info(
            "ヤフーファイナンスから為替レートを取得できませんでした。", exc_info=True
        )
        total_JPY = None

    df = pd.DataFrame(
        {
            "timestamp": datetime.now().isoformat(),
            "conversation": input_path.name[len(ai_name) + 1 :],
            "AI_name": ai_name,
            "entry_URL": url,
            "is_draft": result.get("is_draft"),
            "entry_title": title[:15],
            "entry_content": content[:30],
            "categories": ",".join(categories),
            "custom_prompt": gemini_config["custom_prompt"][:20],
            "model": gemini_config["model"],
            "thinking_budget": gemini_config["thoughts_level"],
            "input_letter_count": len(conversation),
            "output_letter_count": gemini_stats["output_letter_count"],
            "input_tokens": gemini_stats["input_tokens"],
            "input_fee": i_fee,
            "thoughts_tokens": gemini_stats["thoughts_tokens"],
            "thoughts_fee": th_fee,
            "output_tokens": gemini_stats["output_tokens"],
            "output_fee": o_fee,
            "total_fee (USD)": total_fee,
            "total_fee (JPY)": total_JPY,
            "api_key": "..." + gemini_config["gemini_api_key"][-5:],
        },
        index=["vals"],
    )

    output_dir = Path(config["paths"]["output_dir"].strip())
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / (f"summary_{input_path.stem}.txt")
    csv_path = output_dir / "record_test.csv"

    append_csv(csv_path, df)

    summary_path.write_text(content, encoding="utf-8")

    LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    line_text = (
        f"投稿完了です。今日も長い時間お疲れさまでした！\nURL:{url}\nタイトル：{title}"
    )
    if LINE_ACCESS_TOKEN:
        line_message.line_messenger(line_text, LINE_ACCESS_TOKEN)

    return 0


if __name__ == "__main__":

    # config.yamlで設定初期化
    try:
        config, SECRET_KEYS = initialize_config()
    except Exception as e:
        logger.critical(f"CONFIG LOADING ERROR: {e}", exc_info=True)
        sys.exit(1)

    DEBUG_CONFIG = config["other"]["debug"].lower() in ("true", "1", "t")
    # 環境変数の参照結果がFalseの場合configの値を参照
    if DEBUG_ENV:
        DEBUG = DEBUG_ENV
    else:
        DEBUG = DEBUG_CONFIG
        if DEBUG:
            logging.getLogger().setLevel(logging.DEBUG)

    PRESET_CATEGORIES = config["blog"]["preset_category"]
    GEMINI_CONFIG = {
        "custom_prompt": config["ai"]["prompt"],
        "model": config["ai"]["model"],
        "thoughts_level": config["ai"]["thoughts_level"],
        "gemini_api_key": SECRET_KEYS.pop("GEMINI_API_KEY"),
    }
    HATENA_SECRET_KEYS = SECRET_KEYS

    try:
        if len(sys.argv) > 1:
            input_path = Path(sys.argv[1])
            logger.info(f"処理を開始します: {input_path.name}")
        else:
            logger.info("エラー: ファイル名が正しくありません。実行を終了します")
            sys.exit(1)

        exit_code = main(  # メイン処理
            input_path,
            PRESET_CATEGORIES,
            GEMINI_CONFIG,
            HATENA_SECRET_KEYS,
            debug_mode=DEBUG,
        )

        logger.info("アプリケーションは正常に終了しました。")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(
            "エラーが発生しました。app.logで詳細を確認してください。\n実行を終了します。",
            exc_info=True,
        )
        sys.exit(1)
