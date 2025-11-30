# chatbot-logger

**🚧 開発中のプロジェクト 🚧**

対話形AIとのログをAIが分析し、学習記録としてはてなブログへ投稿するツール。

## 基本的な使い方
- 下記Chrome拡張機能で2クリックでjsonファイルをDL
- jsonファイルをショートカットへドラッグアンドドロップ
- その日に行われた一連の会話だけをプログラムが抽出（Claudeログの場合）
- 会話をGemini 2.5 proが自動で要約、タイトル、カテゴリーを決定
- その内容をはてなブログへ自動投稿

- Claude, ChatGPT, Geminiに対応

## 実行環境

- **Python 3.13 以上**
- 主要依存ライブラリ:
  - `google-genai`
  - `pydantic`
  - `requests-oauthlib`
  - 詳しくは `requirements.txt` を参照

## 📋 セットアップ

### 0. ルートディレクトリで仮想環境を作成、pipインストール
```bash
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 1. Chrome拡張機能のインストール

- **Claude Exporter**: https://chromewebstore.google.com/detail/claude-exporter-save-clau/elhmfakncmnghlnabnolalcjkdpfjnin
- **Gemini Exporter**: https://chromewebstore.google.com/detail/gem-chat-exporter-gemini/jfepajhaapfonhhfjmamediilplchakk
- **ChatGPT Exporter**: https://chromewebstore.google.com/detail/chatgpt-exporter-chatgpt/ilmdofdhpnhffldihboadndccenlnfll

### 2. API認証情報の設定

`.env`ファイルを作成し、APIキーを設定、初期設定：
```env
GEMINI_API_KEY=your_gemini_api_key
HATENA_CONSUMER_KEY=your_consumer_key
...
```
#### はてなブログOAuth認証
はてなブログの`consumer key`, `consumer secret`を取得：
https://developer.hatena.ne.jp/ja/documents/auth/apis/oauth/consumer

`token_request.py`でOAuth認証（初回のみ）
---追記予定

### 3. drag_and_drop.batのショートカットを使いやすい場所に設置


## 📖 使用方法

### 1. 対話ログエクスポート
Claude/ChatGPT/Gemini Exporterを使用してClaudeとの対話をjson形式でエクスポート

### 2. drag_and_drop.batのショートカットにjsonをドラッグ・アンド・ドロップ

### 3. 結果確認
- ターミナルが開きブログ投稿の内容・URLを表示
- `outputs/`フォルダに最新の投稿とCSVファイルを出力（追記）


## 🔧 開発予定・課題

- [ ] **投稿完了通知機能** - LINEとの連携を考え中
- [ ] **はてな初回OAuth認証の簡素化・ガイダンス作成** - まずこのREADMEを充実させる
- [ ] **GUI追加** - 設定・実行の簡易化
- [ ] **ログレベル改善** - 構造化ログ・デバッグ機能強化
- [ ] **エラー処理強化** - API制限・ネットワークエラー等
- [ ] **GoogleSheets連携** - csv自動追記でどこでもログ確認
- [ ] **フォルダ監視** - ファイル追加時の自動実行

## ✅ 実装済み機能

- **対話型ログ解析**: Claude ExporterでエクスポートしたJSONファイルをAI用に処理
- **AI要約**: Google Gemini APIで対話内容の要約を出力
- **はてなブログ投稿**: ブログ記事として投稿
- **コスト分析**: トークン使用量と料金記録（JPY換算） ※基本はGemini 2.5 無料枠での使用を想定
- **設定検証**: 起動時の設定ファイル・APIキー検証

## 📁 プロジェクト構成

```
chatbot-logger/
├── main.py              # メインスクリプト
├── ai_client.py         # Gemini API接続
├── json_loader.py       # JSONファイル処理
├── uploader.py          # ブログ投稿機能
├── token_request.py     # はてな初回OAuth認証用スクリプト
├── drag_and_drop.bat    # 🎯 ドラッグ＆ドロップ起動スクリプト
├── config.yaml          # 設定ファイル
├── .env                 # 環境変数設定 (APIキーなど)
├── requirements.txt     # 依存関係
├── outputs/             # 出力フォルダ
└── tests/               # テストファイル
```

## 技術スタック
- OAuth 1.0a (requests-oauthlib)
- Gemini API 構造化出力
- Pydantic (データバリデーション)

## 📝 ライセンス

個人プロジェクト（開発中）
