import asyncio
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import gspread
import httpx
import yfinance as yf

from . import json_loader as jl
from . import line_message
from .blog.blog_schema import (
    AbstractBlogPoster,
    BaseBlogResponse,
    BlogClientSchema,
    HatenaResponseSchema,
    HatenaSecretKeys,
)
from .blog.devto_poster import DevToPoster
from .blog.hatenablog_poster import HatenaBlogPoster
from .blog.qiita_poster import QiitaPoster
from .llm import deepseek_client, gemini_client
from .llm.conversational_ai import ConversationalAi, LlmConfig
from .setup import initialization
from .types import BlogServices, TypeBlogResult

logger = logging.getLogger(__name__)
parent_logger = logging.getLogger("cha2hatena")

try:
    DEBUG, secret_keys, llm_config, CONFIG = initialization(parent_logger)
except Exception as e:
    logger.critical(f"初期設定が正常に行われませんでした: {e}", exc_info=True)
    sys.exit(1)

# -------


def create_ai_client(config: LlmConfig):
    if config.model.startswith("gemini"):
        client = gemini_client.GeminiClient(config)
    elif config.model.startswith("deepseek"):
        client = deepseek_client.DeepseekClient(config)
    else:
        logger.error("モデル名が正しくありません。実行を中止します。")
        logger.error(f"モデル名: {config.model}")
    return client


async def process_blogpost(schema: BlogClientSchema) -> TypeBlogResult:
    """複数のブログへ投稿 投稿結果を辞書のリストで返却"""
    BLOG_CLIENTS: list[tuple[BlogServices, AbstractBlogPoster]] = []
    if schema.hatena_secret_keys:
        BLOG_CLIENTS.append((BlogServices.HATENA, HatenaBlogPoster))
    if schema.qiita_bearer_token:
        BLOG_CLIENTS.append((BlogServices.QIITA, QiitaPoster))
    if schema.devto_api_key:
        BLOG_CLIENTS.append((BlogServices.DEVTO, DevToPoster))

    clients = {name: client_class.model_validate(schema.model_dump()) for name, client_class in BLOG_CLIENTS}

    async with httpx.AsyncClient() as httpx_client:
        tasks = [client.blog_post(httpx_client) for client in clients.values()]
        results: BaseBlogResponse | BaseException = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        name: {"result": result, "success": not isinstance(result, BaseException)}
        for name, result in zip(clients.keys(), results)
    }


def append_csv(path: Path, data: dict) -> None:
    """pathがなければ作成し、CSVに1行追記"""
    # ファイルを開く前に状態を確定させる（正しい）
    is_new_file = not path.exists() or path.stat().st_size == 0

    try:
        with path.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if is_new_file:
                writer.writeheader()  # 新規または空の時のみ列名を追加
            writer.writerow(data)

        if is_new_file:
            logger.warning(f"新しいCSVファイルを作成しました: {path}")
        else:
            logger.warning(f"CSVにデータを追記しました: {path.name}")
    except Exception:
        logger.exception("CSVファイルへの書き込み中にエラーが発生しました。")


def to_spreadsheet(new_data: dict, spreadsheet_name: str) -> None:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    CREDENTIALS_DIRECTORY = Path.cwd() / "credentials" / "credentials.json"
    if spreadsheet_name:
        gc = gspread.service_account(scopes=SCOPES, filename=CREDENTIALS_DIRECTORY)
        try:
            # スプレッドシートを開く（存在チェック）
            sh = gc.open(spreadsheet_name)
            worksheet = sh.sheet1

            existing_data = worksheet.get_all_values()
            if not existing_data:
                worksheet.update([list(new_data.keys())] + [list(new_data.values())])
                logger.warning(f"新規作成: スプレッドシートにヘッダーとデータを追加しました: {spreadsheet_name}")
            else:
                worksheet.append_row(list(new_data.values()))
                logger.warning("追記: スプレッドシートに新しい行を追加しました")

        except gspread.exceptions.SpreadsheetNotFound:
            # スプレッドシートが存在しない場合、新規作成
            sh = gc.create("record")
            worksheet = sh.sheet1
            worksheet.update([list(new_data.keys())] + [list(new_data.values())])
            logger.warning(f"新規スプレッドシートを作成し、データを追加しました: {spreadsheet_name}")


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

        # JSONファイルから会話履歴を読み込み、テキストに整形
        llm_config.conversation = jl.json_loader(input_paths)

        # AIオブジェクト作成
        ai_instance: ConversationalAi = create_ai_client(llm_config)

        # AIで要約取得
        llm_outputs, llm_stats = ai_instance.get_summary()

        #
        blog_post_kwargs = BlogClientSchema(
            **llm_outputs,
            preset_categories=(CONFIG.get("blog") or {}).get("preset_category", []),
            hatena_secret_keys=HatenaSecretKeys.model_validate(secret_keys),
            qiita_bearer_token=secret_keys.get("qiita_bearer_token"),
            devto_api_key=secret_keys.get("devto_api_key"),
            author=None,  # str | None   Noneの場合自分のはてなID
            updated=None,  # datetime | None  公開時刻設定。Noneの場合5分後に公開
            is_draft=DEBUG,  # デバッグ時は下書き
        )
        blogpost_results: TypeBlogResult = asyncio.run(process_blogpost(blog_post_kwargs))

        # 結果の整理
        urls = {}
        hatena_error = False
        for service, report in blogpost_results.items():
            _result: BaseBlogResponse | BaseException = report["result"]
            if isinstance(_result, BaseBlogResponse):
                urls[service] = _result.url

                if service is BlogServices.HATENA:
                    hatena_result: HatenaResponseSchema = _result
            else:
                logger.error(f"{service.value}の処理でエラー。投稿されませんでした。エラー内容:\n{_result}")
                hatena_error = service is BlogServices.HATENA

        if hatena_error:
            logger.error("はてな投稿エラーのため実行を中止します。")
            logger.error(
                f"Qiita URL:{urls.get(BlogServices.QIITA, '')}\nDev.to URL: {urls.get(BlogServices.DEVTO, '')})"
            )

        print("-" * 50)
        print(f"投稿タイトル：{hatena_result.title}")
        print(f"\n{'-' * 20}投稿本文{'-' * 20}")
        print(f"{hatena_result.content[:100]}")
        print("-" * 50)

        # LINE通知テキスト整形

        line_access_token = secret_keys.get("line_channel_access_token")
        if line_access_token:
            line_text = "投稿完了です。今日もお疲れさまでした！\n"
            line_text += f"タイトル：{hatena_result.title}\n"
            for name, url in urls.items():
                line_text += f"{name}: {url}\n" if url else ""
                
            line_text += f"はてな編集: {hatena_result.url_edit}\n"
            line_text += f"下書きモード: {hatena_result.is_draft}"

            try:
                line_message.line_messenger(line_text, line_access_token)
            except Exception as e:
                logger.error("エラー：LINE通知は行われませんでした。")
                logger.info(f"詳細: {e}")
        else:
            line_text = "要約の保存完了。ブログ投稿は行われませんでした。今日も長い時間お疲れ様でした。\n"
            line_text += f"本文: \n{hatena_result.content[:200]} ..."


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

        csv_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation_title": conversation_titles,
            "AI_name": " ".join(ai_names),
            "entry_URL": hatena_result.url,
            "is_draft": hatena_result.is_draft,
            "entry_title": hatena_result.title,
            "entry_content": hatena_result.content[:30],
            "categories": ",".join(hatena_result.categories),
            "prompt": llm_config.prompt[:20],
            "model": llm_config.model,
            "temperature": llm_config.temperature,
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
            "api_key": "..." + llm_config.api_key[-5:],
            "Qiita_URL": urls.get(BlogServices.QIITA, ""),
            "Dev.to_URL": urls.get(BlogServices.DEVTO, ""),
        }

        summary_file_name = datetime.now().strftime("%y%m%d") + "-" + hatena_result.title

        csv_dir = Path(CONFIG["paths"]["output_dir"].strip())
        csv_dir.mkdir(exist_ok=True)
        csv_path = csv_dir / "record.csv"
        summary_dir = csv_dir / "summary"
        summary_dir.mkdir(exist_ok=True)
        summary_path = summary_dir / (f"{summary_file_name.replace('/', ', ')}.txt")
        # ファイル出力
        append_csv(csv_path, csv_data)
        summary_path.write_text(hatena_result.content, encoding="utf-8")

        # Googleスプレッドシートへ出力
        if not DEBUG and (CONFIG.get("google_sheets") or {}).get("enable"):
            SPREADSHEET_NAME = (CONFIG.get("google_sheets") or {}).get("spreadsheet_name", "record")
            try:
                to_spreadsheet(csv_data, SPREADSHEET_NAME)
            except Exception as e:
                logger.warning("Googleスプレッドシートへの書き込みは行われませんでした")
                logger.debug(f"詳細: {e}")

        logger.info("処理が正常に終了しました。")
        return 0

    except Exception:
        logger.error("アプリケーションの実行を中止します。")
        logger.info("詳細: ", exc_info=True)
        sys.exit(1)
        sys.exit(1)
