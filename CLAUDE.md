# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`cha2hatena`: AI チャットログ（Claude/ChatGPT/Gemini Exporter の JSON、または .txt/.md）を読み込み、Gemini または DeepSeek でブログ記事（title/content/categories）に要約し、はてなブログ（必須）・Qiita・Dev.to（任意）へ投稿、LINE 通知・CSV/Google Sheets にコスト記録するCLI。コメント・ログメッセージ・コミットメッセージは日本語。

## Commands

依存管理は uv（`uv.lock`）。dev ツールは `[dependency-groups] dev`（pytest, pytest-asyncio, ruff, mypy）。

```bash
uv sync                                   # 依存インストール（dev含む）
uv run cha2hatena sample/Claude-sample.json [more.json ...]   # 実行（= python -m cha2hatena）
uv run pytest                             # 全テスト
uv run pytest tests/test_ai_client.py::test_gemini_client_get_summary_uses_mocked_google_sdk  # 単体
uv run ruff check . && uv run ruff format .   # line-length 120, target py313
uv run mypy src
```

- **テスト・実行は必ずリポジトリ直下から**。`config.yaml` と `.env` をカレントディレクトリから読み、`app.log` もカレントに書く。
- `DEBUG=true`（.env）または `config.yaml` の `other.debug` でデバッグモード → ログレベル DEBUG、ブログは**下書き投稿**、Google Sheets 書き込みはスキップ。
- `token_request.py` ははてな OAuth 1.0a のアクセストークン初回取得用スクリプト。

## Architecture

処理フローは `src/cha2hatena/main.py:main()` に集約：

1. `json_loader.json_loader(paths)` — 複数ファイルを 1 つの会話テキストに整形。ファイル名の接頭辞（`Claude-`, `ChatGPT-`, `Gemini-`, `Deepseek-`）で AI 名を判定。JSON は `messages` 配列を末尾から遡り、最新メッセージと別日かつ 3 時間以上空いたところで打ち切る（=「その日の会話」だけ抽出）。Exporter 形式（`role`/`say`/`time`）と Claude-Conversation-Extractor 形式（`content`/`timestamp`）の両方に対応。
2. `create_ai_client(llm_config)` — `config.yaml` の `ai.model` の接頭辞（`gemini`/`deepseek`）で `llm/` 配下の `ConversationalAi` 実装を選択。`get_summary()` は `(dict{title,content,categories}, TokenStats)` を返す。Gemini は `AiOutput` の JSON スキーマで構造化出力。料金は `llm_stats.TokenStats` の property で遅延計算（モデル別単価は `LlmFee`）。新モデル対応時は単価表の更新が必要。
3. `BlogClientSchema` に LLM 出力と秘密鍵を詰め、`process_blogpost()` で有効なポスター（`blog/` の `HatenaBlogPoster`/`QiitaPoster`/`DevToPoster`、いずれも `AbstractBlogPoster` = pydantic BaseModel）を `model_validate(schema.model_dump())` で生成し、共有 `httpx.AsyncClient` 上で `asyncio.gather(..., return_exceptions=True)` 並列投稿。各ポスターは Field alias で共通スキーマのフィールド名を各 API のフィールド名に対応付ける（例: Dev.to は `published` が is_draft の反転）。
4. 結果集計 → LINE 通知（`line_message.py`）→ yfinance で USD/JPY 換算 → `outputs/record.csv` と `outputs/summary/*.txt` に保存 → 任意で Google Sheets（`credentials/credentials.json` のサービスアカウント）。

### 注意点
- **`cha2hatena.main` と `cha2hatena.setup` は import 時に副作用がある**：`setup.initialization()` がロガー設定・`config.yaml`/`.env` 読み込み・`LlmConfig` 生成を行う。テストで `main` を import するだけで設定ファイルが必要になる。
- 秘密鍵は `setup.config_setup()` で `.env` から一元取得（キー一覧は `.env.sample`）。Qiita/Dev.to のトークンは `config.yaml` の `blog.qiita`/`blog.devto` が true の時だけ読まれる。
- はてな投稿は Authlib の `OAuth1Auth` + `httpx.AsyncClient`。**`openai<3` の固定を外さないこと**：openai 3 系が `httpx2` を持ち込むと Authlib が `httpx2.Auth` を選び、`httpx.AsyncClient` で `TypeError: Invalid "auth" argument` になる（詳細 `DEPENDENCY_COMPATIBILITY.md`）。
- テストは**通信なしの単体テストのみ**。HTTP は `httpx.MockTransport` で差し替え、レスポンスは `sample/` の実データを使う。Gemini SDK（`google.genai`）は `GeminiClient.get_summary()` 内で遅延 import しているので、`sys.modules` に偽モジュールを差し込んでモックする（`tests/test_ai_client.py`）。
- 読み込み層・ポスターの BaseModel 構造は今後ゆるめる予定なので、テストは内部ヘルパーやフィールド構造ではなく入出力（ファイル→会話テキスト、記事データ→HTTPリクエスト、HTTPレスポンス→結果）を検証する。
- `tests/` 内の `gspread_example.py`, `sheets_quickstart.py`, `official_sample.py`, `notify.py` はテストではなく手動実験用スクリプト。
- `sample/` に各サービスの入出力サンプル（Exporter JSON、はてな Atom XML、Qiita/Dev.to レスポンス）がある。

## In-progress: MCP サーバー化（`refac/mcp` ブランチ）
`TODO_MCP.md` 参照。方針：はてな投稿の必須要件を外す（秘密鍵の Optional 化、`setup.py` の取得チェック削除、メインフローのデータ型固定の解除）、JSON 処理層にインターフェースを挟んで DI 化。LLM 層とブログのレスポンススキーマは既に分離済み。
