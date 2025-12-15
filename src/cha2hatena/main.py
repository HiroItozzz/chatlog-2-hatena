import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from . import hatenablog_poster, line_message
from . import json_loader as jl
from .llm import deepseek_client, gemini_client
from .llm.conversational_ai import ConversationalAi, LlmConfig
from .setup import initialization

logger = logging.getLogger(__name__)
parent_logger = logging.getLogger("cha2hatena")

try:
    DEBUG, SECRET_KEYS, LLM_CONFIG, config = initialization(parent_logger)
except Exception as e:
    logger.critical(f"初期設定が正常に行われませんでした: {e}", exc_info=True)
    sys.exit(1)


PRESET_CATEGORIES = config["blog"]["preset_category"]
LINE_ACCESS_TOKEN = SECRET_KEYS.pop("LINE_CHANNEL_ACCESS_TOKEN")
HATENA_SECRET_KEYS = SECRET_KEYS


######################################################


def create_ai_client(config: LlmConfig):
    if config.model.startswith("gemini"):
        client = gemini_client.GeminiClient(config)
    elif config.model.startswith("deepseek"):
        client = deepseek_client.DeepseekClient(config)
    else:
        logger.error("モデル名が正しくありません。実行を中止します。")
        logger.error(f"モデル名: {config.model}")
    return client


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
            logger.warning(f"新しいCSVファイルを作成しました: {path}")
        else:
            logger.warning(f"CSVにデータを追記しました: {path.name}")
    except Exception:
        logger.exception("CSVファイルへの書き込み中にエラーが発生しました。")
        


def main():
    try:
        logger.debug("================================================")
        logger.debug(f"アプリケーションが起動しました。デバッグモード：{DEBUG}")

        if len(sys.argv) > 1:
            INPUT_PATHS_RAW = sys.argv[1:]
            logger.warning(f"処理を開始します: {', '.join(INPUT_PATHS_RAW)}")
        else:
            logger.error("エラー: 引数を入力する必要があります。実行を終了します")
            sys.exit(1)

        input_paths = list(map(Path, INPUT_PATHS_RAW))

        LLM_CONFIG.conversation = jl.json_loader(input_paths)

        # AIオブジェクト作成
        ai_instance: ConversationalAi = create_ai_client(LLM_CONFIG)

        # AIで要約取得        
        llm_outputs, llm_stats = ai_instance.get_summary()

        # はてなブログへ投稿 投稿結果を辞書型で返却
        blogpost_result = hatenablog_poster.blog_post(
                            **llm_outputs,
                            preset_categories=PRESET_CATEGORIES,
                            hatena_secret_keys=HATENA_SECRET_KEYS, 
                            author=None,  # str | None   Noneの場合自分のはてなID
                            updated=None,  # datetime | None  公開時刻設定。Noneの場合5分後に公開
                            is_draft=DEBUG,  # デバッグ時は下書き                   
                        )
        
        url = blogpost_result.get("link_alternate", "")
        url_edit = blogpost_result.get("link_edit_user", "")
        title = blogpost_result.get("title", "")
        content = blogpost_result.get("content", "")
        categories = blogpost_result.get("categories", [])

        logger.warning("はてなブログへの投稿に成功しました。")
        logger.warning(f"URL: {url_edit}")
        print("-" * 50)
        print(f"投稿タイトル：{title}")
        print(f"\n{'-' * 20}投稿本文{'-' * 20}")
        print(f"{content[:100]}")
        print("-" * 50)

        # LINE通知
        if blogpost_result["status_code"] == 201:
            line_text = "投稿完了です。今日も長い時間お疲れさまでした！\n"
            line_text = (
                line_text + f"タイトル：{title}\n確認: {url}\n編集: {url_edit}\n下書きモード: {blogpost_result.get('is_draft')}"
            )
        else:
            line_text = "要約の保存完了。ブログ投稿は行われませんでした。今日も長い時間お疲れ様でした。\n"
            line_text = line_text + f"タイトル：{title}\n本文: \n{content[:200]} ..."

        try:
            line_message.line_messenger(line_text, LINE_ACCESS_TOKEN)
        except Exception as e:
            logger.error("エラー：LINE通知は行われませんでした。")
            logger.info(f"詳細: {e}")

        # 為替レートを取得
        ticker = "USDJPY=X"
        try:
            dy_rate = yf.Ticker(ticker).history(period="1d").Close.iloc[0]
            total_JPY = llm_stats.total_fee * dy_rate
        except Exception as e:
            logger.error("ヤフーファイナンスから為替レートを取得できませんでした。詳細はapp.logを確認してください")
            logger.info(f"詳細: {e}", exc_info=True)
            total_JPY = None

        ai_names = jl.ai_names_from_paths(input_paths)
        conversation_titles = " ".join(jl.get_conversation_titles(input_paths, ai_names))
        df = pd.DataFrame(
            {
                "timestamp": datetime.now().isoformat(),
                "conversation_title": conversation_titles,
                "AI_name": " ".join(ai_names),
                "entry_URL": url,
                "is_draft": blogpost_result.get("is_draft"),
                "entry_title": title,
                "entry_content": content[:30],
                "categories": ",".join(categories),
                "prompt": LLM_CONFIG.prompt[:20],
                "model": LLM_CONFIG.model,
                "temperature": LLM_CONFIG.temperature,
                "input_letter_count": llm_stats.input_letter_count,
                "output_letter_count": llm_stats.output_letter_count,
                "input_tokens": llm_stats.input_tokens,
                "input_fee": llm_stats.input_fee,
                "thoughts_tokens": llm_stats.thoughts_tokens,
                "thoughts_fee": llm_stats.thoughts_fee,
                "output_tokens": llm_stats.output_tokens,
                "output_fee": llm_stats.output_fee,
                "total_fee (USD)": llm_stats.total_fee,
                "total_fee (JPY)": total_JPY,
                "api_key": "..." + LLM_CONFIG.api_key[-5:],
            },
            index=["vals"],
        )

        summary_file_name = datetime.now().strftime("%y%m%d") + "-" + title

        csv_dir = Path(config["paths"]["output_dir"].strip())
        csv_dir.mkdir(exist_ok=True)
        csv_path = csv_dir / "record.csv"
        summary_dir = csv_dir / "summary"
        summary_dir.mkdir(exist_ok=True)
        summary_path = summary_dir / (f"{summary_file_name.replace('/', ', ')}.txt")
        # 出力
        append_csv(csv_path, df)
        summary_path.write_text(content, encoding="utf-8")
        logger.info("処理が正常に終了しました。")

        return 0

    except Exception:
        logger.error("アプリケーションの実行を中止します。")
        logger.info("詳細: ", exc_info=True)
        sys.exit(1)
