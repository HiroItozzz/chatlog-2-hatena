# chatlog-2-hatena


AIとの会話が保存された特定の形式のJSONファイルを解析・要約。
その内容をはてなブログへ自動投稿するためのツール。  
発端は自分のプログラミング学習の記録用です。

## 基本的な使い方
（下準備： 下記Chrome拡張機能でAIとの対話ログ(.json)をDL）
- jsonファイルをショートカットへドラッグアンドドロップ
- その日に行われた一連の会話を抽出（Claudeログの場合）
- 会話をGemini 2.5 proが自動で要約、タイトル、カテゴリーを決定
- その内容をはてなブログへ自動投稿
- LINEで投稿完了通知


## 実行環境

- **Python 3.10 以上**
- 主要依存ライブラリ:
  - `google-genai`
  - `pydantic`
  - 詳しくは `requirements.txt` を参照


## 📁 プロジェクト構成

```
chatlog-2-Hatena/
├── sample/                          # サンプルファイル・テストデータ
├── src/
│   └── cha2hatena/
│       ├── __init__.py              
│       ├── __main__.py              
│       ├── ai_client.py             # Gemini API接続・構造化出力
│       ├── json_loader.py           # JSONファイル処理・会話抽出
│       ├── line_message.py          # LINE通知モジュール
│       ├── main.py                  # メインロジック
│       ├── uploader.py              # はてなブログ投稿機能
│       └── validate.py              # 設定検証・初期化
├── tests/         
├── .env.sample                      # 環境変数テンプレート
├── .gitignore
├── LICENSE
├── README.md
├── config.yaml                      # アプリケーション設定
├── drag_and_drop.bat                # ドラッグ＆ドロップ起動スクリプト（Windows）
├── pyproject.tom
├── requirements.txt                 # 依存関係
└── token_request.py                 # はてな初回OAuth認証用スクリプト
```


## 📋 セットアップ

### 前提条件
- Python 3.10以上がインストール済み

### 仮想環境構築 (Windows)
```bash
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## 📖 使用方法

### 1. 対話ログエクスポート
Claude/ChatGPT/Gemini Exporterを使用してClaudeとの対話をjson形式でエクスポート

- **Claude Exporter**: https://chromewebstore.google.com/detail/claude-exporter-save-clau/elhmfakncmnghlnabnolalcjkdpfjnin
- **Gemini Exporter**: https://chromewebstore.google.com/detail/gem-chat-exporter-gemini/jfepajhaapfonhhfjmamediilplchakk
- **ChatGPT Exporter**: https://chromewebstore.google.com/detail/chatgpt-exporter-chatgpt/ilmdofdhpnhffldihboadndccenlnfll

### 2. API認証情報の設定

`.env`ファイルを作成し、APIキーを設定、初期設定：
```env
GEMINI_API_KEY=your_gemini_api_key
HATENA_CONSUMER_KEY=your_consumer_key
HATENA_CONSUMER_SECRET=your_consumer_secret
...
```

### 3. はてなブログOAuth認証
はてなブログの`access token`、`access token secret`を取得：

1. https://developer.hatena.ne.jp/ja/documents/auth/apis/oauth/consumer を参照
2. `token_request.py`を実行してOAuth認証フローを完了
3. 取得したトークンを`.env`に追記

```bash
python token_request.py
```

### 4. config.yamlの設定
```yaml
ai:
  model: gemini-2.5-pro
  prompt: "please summarize the following conversation for my personal blog article..."
  thoughts_level: -1  # または 128-24576

blog:
  preset_category:
    - プログラミング
    - 学習ログ
...
```

### 5. 実行方法

**ドラッグアンドドロップ（推奨・Windows）:**
- `drag_and_drop.bat`にエクスポートしたJSONファイルをドラッグ&ドロップ
- 仮想環境の存在確認とパッケージ依存関係の自動チェック機能付き

**コマンドラインでの実行:**
```bash
python -m cha2hatena path/to/conversation.json
```

複数ファイルも可能：
```bash
python -m cha2hatena file1.json file2.json file3.json
```

### 6. 結果確認
- LINEで投稿完了通知が送信される
- `outputs/record.csv` に実行履歴・コスト（トークン数と料金）が記録される
- `outputs/{title}.txt` に投稿本文がテキストとして保存される

## 技術スタック
- OAuth 1.0a (requests-oauthlib)
- Gemini API 構造化出力（Pydantic）
- JSON・XML処理（ElementTree）
- 外部API統合（はてなブログAtom API、LINE Messaging API）


## 🔧 開発予定・課題

- [ ] はてな投稿・LINE通知のそれぞれのオンオフを可能に - 現在は設定検証の範囲が広すぎるため使い勝手が悪い
- [ ] LINE通知メッセージ内容強化 - アップロードするとAI生成による好きなタイプの労いの言葉が返ってくるように
- [ ] GUI追加 - 設定・実行の簡易化
- [ ] GoogleSheets連携 - csv自動追記でどこでもログ確認
- [ ] UXの改善 - フォルダ監視...？


### ✅ 実装済み

- パッケージ化（`src/cha2hatena/`構成）
- 複数ファイル入力対応 - 複数のスレッドのログもまとめてGeminiへ入力
- 投稿完了通知機能 - LINEとの連携
- はてなブログ投稿: ブログ記事として投稿
- コスト分析: 入出力トークン使用量と料金記録（JPY換算） ※基本はGemini-2.5-pro無料枠利用
- AI要約: Google Gemini APIで対話内容の要約を出力
- 対話型ログ解析: Claude ExporterでエクスポートしたJSONファイルをAI用に処理

## 工夫したこと
- Gemini構造化出力（`pydantic`を使用）によってGeminiによる出力をjson形に限定
  - はてなへの入力（XML形式、タイトル・内容・カテゴリ）との一致を強く保証
- エラーハンドリング
  - Chrome拡張機能由来のjson処理、外部接続3回のパイプラインでのエラー原因特定に十分な程度に
- 定数をメイン処理で定義・辞書に格納し、引数を下層まで受け渡す構成（可読性）
  - 最後は`**dict`で処理

## このプロジェクトで学んだこと
- HTTPメソッドとRESTの考え方
- HTTPレスポンスコードによる場合分けの仕方
- XML形式の取り扱い（ElementTree、名前空間、XPath）
- ログレベルの使い分け
- gitのブランチとプルリクエストの使い方
- Pythonパッケージング（`__main__.py`の意味、pyproject.toml）

## 感じたこと

ずっと対話型AIとやり取りしながらコードを書いている中で、整理しづらい有用なログが毎日溜まる状況で、これを使ってなにか出来ないかと思っていました。  
当初はフォルダ監視での運用を目標に考えていたけれども、ドラッグアンドドロップは個人用途では必要十分だと現状では感じています。  
懸念点は拡張機能への依存ですが、将来的にはこの部分も書けるようになれればと考えています。  
また、今回はVSCodeのコード補完機能を使わずに書きました。リファクタを繰り返す中で徐々に良いロジックになっていくプロセスが楽しく、プログラミングの面白さを強く感じた思い出のプロジェクトとなりそうです。

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## 参考資料

- https://ai.google.dev/gemini-api/docs?hl=ja
- https://developer.hatena.ne.jp/ja/documents/blog/apis/atom/
- https://developers.line.biz/ja/reference/messaging-api/#send-broadcast-message
- https://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html
- https://qiita.com/jksoft/items/4d57a9282a56c38d0a9c
