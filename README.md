# chatlog-2-hatena


AIとの会話が保存された特定の形式のJSONファイルを解析・要約。
その内容をはてなブログへ自動投稿するためのツール。  
発端は自分のプログラミング学習の記録用です。
- 実際の投稿: https://d3c0.hatenablog.com/entry/2025/12/08/174957

## 基本的な使い方
（下準備： 下記Chrome拡張機能でAIとの対話ログ(.json)をDL）
- jsonファイルをショートカットへドラッグアンドドロップ
- その日に行われた一連の会話を抽出（Claudeログの場合）
- 会話をGeminiまたはDeepseekが自動で要約、タイトル、カテゴリーを決定
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
├── src/cha2hatena/          # メインパッケージ
├── sample/                  # サンプルファイル
├── tests/                   # テストコード
├── .env.sample              # 環境変数テンプレート
├── config.yaml              # アプリケーション設定
├── drag_and_drop.bat        # Windows用起動スクリプト
├── requirements.txt         # 依存関係
└── token_request.py         # はてな初回OAuth認証用（最初に1度だけ実行）
```
## 📋 セットアップ

```bash
# 仮想環境を構築 (Windows)
python -m venv .venv
.venv\Scripts\activate

# インストール
pip install -e .
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
DEEPSEEK_API_KEY=your_deepseek_api_key  # geminiとdeepseekの少なくとも一方を入力
HATENA_CONSUMER_KEY=your_consumer_key
HATENA_CONSUMER_SECRET=your_consumer_secret
...
```

### 3. はてなブログOAuth認証
はてなブログの`access token`、`access token secret`を取得、`.env`で設定：

1. https://developer.hatena.ne.jp/ja/documents/auth/apis/oauth/consumer を参照
2. `token_request.py`を実行してOAuth認証フローを完了
3. 取得したトークンを`.env`に追記

```bash
python token_request.py
```

### 4. config.yamlの設定
```yaml
ai:
  model: gemini-2.5-flash # または Gemini-2.5-pro
  prompt: "please summarize the following conversation for my personal blog article..."
  thoughts_level: -1  # 思考レベルの設定: "-1"は動的思考

blog:
  preset_category:
    - プログラミング
    - 学習ログ
...
```

### 5. 実行方法

**ドラッグアンドドロップ（Windows）:**
- `drag_and_drop.bat`にエクスポートしたJSONファイル（複数可）をドラッグ&ドロップ

**コマンドライン:**
```bash
cha2hatena file1.json file2.json file3.json
```

```bash
python -m cha2hatena path/to/conversation.json
```

### 6. 結果確認
- LINEで投稿完了通知を送信
- `outputs/record.csv` に実行履歴・コスト（トークン数と料金）を記録
- `outputs/{title}.txt` に投稿本文をテキストとして保存

## 技術スタック
- OAuth 1.0a (requests-oauthlib)
- Gemini API 構造化出力（Pydantic）
- JSON・XML処理（ElementTree）
- 外部API統合（はてなブログAtom API、LINE Messaging API）


## 🔧 開発予定・課題

- [ ] LINE通知メッセージ内容強化 - アップロードするとAI生成による好きなタイプの労いの言葉が返ってくるように

### ✅ 実装済み
- GoogleSheets連携: ルートディレクトリに`credentials.json`を配置することでGoogle Sheetsに記録可能
- .txtファイル入力対応
- Deepseekによる要約に対応
- パッケージ化（`src/cha2hatena/`構成）
- 複数ファイル入力対応
- 投稿完了LINE通知機能
- はてなブログ投稿
- コスト分析: 入出力トークン使用量と料金記録（JPY換算）
- AI要約: Google Gemini APIで対話内容の要約を出力
- 対話型ログ解析: Claude ExporterでエクスポートしたJSONファイルをAI用に処理

## 工夫したこと
- Gemini構造化出力（`Pydantic`利用）によってGeminiからの出力をjson形に限定
  - はてなへの入力（XML形式、タイトル・内容・カテゴリ）との一致を強く保証
- `logging`のHandler設定・出力設定  
  - CLIアプリのため標準出力(StreamHandler)とファイル出力(RotatingFileHandler)を個別に調整
  - エラー詳細はログファイル確認へ誘導
- 鍵の一元管理（`setup.py`）
- 使用トークンを保持するクラス(`TokenStats`)のプロパティの構成
  - 初期化時はトークン数のみ入力。実コスト(米ドル換算)は`@property`で遅延計算
  
## このプロジェクトで学んだこと
- HTTPメソッドとRESTの考え方
- HTTPレスポンスコードによる場合分けの仕方
- XML形式の取り扱い（ElementTree、名前空間、XPath）
- gitのブランチとプルリクエストの使い方
- パッケージングの方法（`__main__.py`の意味、pyproject.toml等）
  - 単体モジュールやライブラリとしての外部利用のしやすさの観点
- 基本的には辞書ではなくクラスがよいという発想
  - IDEによる自動補完が聞く点
  - Pydanticによる型安全性、ABCを利用したダックタイピング

## 感じたこと

ずっと対話型AIとやり取りしながらコードを書いている中で、整理しづらい有用なログが毎日溜まる状況で、これを使ってなにか出来ないかと思っていました。  
当初はフォルダ監視での運用を目標に考えていたけれども、ドラッグアンドドロップは個人用途では必要十分だと現状では感じています。  
懸念点は拡張機能への依存ですが、将来的にはこの部分も書けるようになれればと考えています。  
また、今回はVSCodeのコード補完機能を使わずに書きました。リファクタを繰り返す中で徐々に良いロジックになっていくプロセスが楽しく、プログラミングの面白さを強く感じた思い出のプロジェクトとなりそうです。

## License

MIT LICENSE

## 参考資料

- https://ai.google.dev/gemini-api/docs?hl=ja
- https://developer.hatena.ne.jp/ja/documents/blog/apis/atom/
- https://developers.line.biz/ja/reference/messaging-api/#send-broadcast-message
- https://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html
- https://qiita.com/jksoft/items/4d57a9282a56c38d0a9c
- https://api-docs.deepseek.com/
- https://developers.google.com/workspace/sheets/api/quickstart/python?hl=ja
- https://docs.gspread.org/en/latest/#