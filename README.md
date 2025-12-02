# chatbot-logger

**🚧 開発中のプロジェクト 🚧**

対話形AIとのログをAIが分析し、学習記録としてはてなブログへ投稿するツール。
初回の認証が複雑なため現在は個人用

## 基本的な使い方
- 下記Chrome拡張機能で2クリックでjsonファイルをDL
- jsonファイルをショートカットへドラッグアンドドロップ
- その日に行われた一連の会話だけをプログラムが抽出（Claudeログの場合）
- 会話をGemini 2.5 proが自動で要約、タイトル、カテゴリーを決定
- その内容をはてなブログへ自動投稿
- LINEで投稿完了通知

- Claude, ChatGPT, Geminiに対応

## 実行環境

- **Python 3.13 以上**
- 主要依存ライブラリ:
  - `google-genai`
  - `pydantic`
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
- LINEでURL確認！アクセス。
- `outputs/`フォルダに最新の投稿とCSVファイルを出力/追記


## 🔧 開発予定・課題

- [ ] **AIによるLINE通知メッセージ** - アップロードすると労いの言葉がかえってくる
- [ ] **GUI追加** - 設定・実行の簡易化
- [ ] **GoogleSheets連携** - csv自動追記でどこでもログ確認
- [ ] **UXの改善** - フォルダ監視...？完了


### ✅ 実装済み

- [x] **ログレベル改善** - 構造化ログ・デバッグ機能強化
- [x] **エラー処理強化** - API制限・ネットワークエラー等
- [x] **投稿完了通知機能** - LINEとの連携を考え中
- **対話型ログ解析**: Claude ExporterでエクスポートしたJSONファイルをAI用に処理
- **AI要約**: Google Gemini APIで対話内容の要約を出力
- **はてなブログ投稿**: ブログ記事として投稿
- **コスト分析**: 入出力トークン使用量と料金記録（JPY換算） ※基本はGemini-2.5-pro 無料枠

## 📁 プロジェクト構成

```
chatbot-logger/
├── main.py              # メインスクリプト
├── validate.py          # 設定検証スクリプト
├── json_loader.py       # JSONファイル処理
├── ai_client.py         # Gemini API接続
├── uploader.py          # ブログ投稿機能
├── line_message.py      # LINE通知モジュール
├── token_request.py     # はてな初回OAuth認証用スクリプト
├── drag_and_drop.bat    # 🎯 ドラッグ＆ドロップ起動スクリプト
├── config.yaml          # 設定ファイル
├── .env                 # 環境変数 (APIキーなど)
├── requirements.txt     # 依存関係
├── outputs/             # 出力フォルダ
└── tests/               # テストファイル
```

## 技術スタック
- OAuth 1.0a (requests-oauthlib)
- Gemini API 構造化出力
- Pydantic (データバリデーション)

## このプロジェクトで学んだこと（現時点）
- エラーログ出力（logging）
- HTTPメソッドとREST APIの思想
- HTTPレスポンスコードによる場合分けの仕方
- 定数はメイン処理で定義し下層まで受け渡し
- XML形式の取り扱い（ElementTree、名前空間）
- .envとconfigの使い分け
- gitのbranchとPRの使い方

## 感じたこと

ずっと対話型AIとやり取りしながら1日作業している中で、整理しづらい有用なログがたくさん溜まっており、なにか出来ないかと思っていたのがきっかけでした。  
当初はフォルダ監視での運用を目標に考えていましたが、ドラッグアンドドロップが個人用途では最適解かもなと思っています。  
最大の懸念点は拡張機能への依存ですが、将来的にはこの部分も自分で書ければなと思っています。  
また、今回はVSCodeのコード補完機能を使わずに書きました。リファクタを繰り返す中で徐々に良いロジックになっていくことの、プログラミングの面白さを強く感じた思い出のプロジェクトとなりました。

## 📝 ライセンス

個人プロジェクト（開発中）
