# chatbot-logger

**🚧 開発中のプロジェクト 🚧**

AIチャットボットとの対話ログを分析し、学習記録としてブログ投稿するツールです。
現在はClaudeの対話ログのみ対応、手動実行版です。

## ✅ 実装済み機能

- **Claudeログ解析**: Claude ExporterでエクスポートしたJSONファイルを処理
- **AI要約**: Google Gemini APIで対話内容を日本語要約・構造化
- **はてなブログ投稿**: 手動実行でブログ記事として投稿
- **コスト分析**: トークン使用量と料金記録（USD/JPY換算）
- **設定検証**: 起動時の設定ファイル・APIキー検証

## 🔧 開発予定・課題

- [ ] **ChatGPT・Geminiログ対応** - 現在はClaude形式のみ
- [ ] **フォルダ監視機能** - ファイル追加時の自動実行
- [ ] **バッチ処理** - 複数ファイルの一括処理
- [ ] **ログレベル改善** - 構造化ログ・デバッグ機能強化
- [ ] **エラー処理強化** - API制限・ネットワークエラー対応
- [ ] **GUI追加** - 設定・実行の簡易化

## 📋 必要な準備

### 1. Chrome拡張機能のインストール
**現在はClaudeのみ対応**：

- **Claude Exporter**: https://chromewebstore.google.com/detail/claude-exporter-save-clau/elhmfakncmnghlnabnolalcjkdpfjnin

※ ChatGPT Exporterは実装予定

### 2. API認証情報の取得

#### Google Gemini API
1. [Google AI Studio](https://aistudio.google.com/)でAPIキーを取得
2. `.env`ファイルに`GEMINI_API_KEY=your_api_key`を設定

#### はてなブログAPI
はてなブログのconsumer key, consumer secretを取得：
https://developer.hatena.ne.jp/ja/documents/auth/apis/oauth/consumer

## 🛠 セットアップ

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. 環境設定
`.env`ファイルを作成し、APIキーを設定：
```env
GEMINI_API_KEY=your_gemini_api_key
```

### 3. 設定ファイル調整
`config.yaml`でプロンプトや出力設定をカスタマイズできます：

```yaml
ai:
  model: "gemini-2.5-pro"
  thoughts_level: -1  # 動的思考レベル
  prompt: |
    # カスタムプロンプト...
```

## 📖 使用方法（現在は手動実行のみ）

### 1. 対話ログの準備
Claude Exporterを使用してClaudeとの対話をJSONファイルでエクスポート

### 2. ファイルパス設定
`main.py`の`INPUT_PATH`を手動で変更：
```python
INPUT_PATH = Path(r"path/to/your/exported.json")
```

### 3. 実行
```bash
python main.py
```

### 4. 結果確認
- `outputs/`フォルダに要約テキストが保存
- `record.csv`にコスト分析結果が記録
- はてなブログに投稿（成功時）

**注意**: 現在は1ファイルずつの手動処理です

## 📁 プロジェクト構成

```
chatbot-logger/
├── main.py              # メインスクリプト
├── ai_client.py         # Gemini API接続
├── json_loader.py       # JSONファイル処理
├── uploader.py          # ブログ投稿機能
├── config.yaml          # 設定ファイル
├── requirements.txt     # 依存関係
├── sample/              # サンプルデータ
├── outputs/             # 出力フォルダ
└── tests/              # テストファイル
```

## 🔧 主要コンポーネント

### BlogParts モデル
```python
class BlogParts(BaseModel):
    title: str           # ブログタイトル
    content: str         # 本文（Markdown）
    categories: List[str] # カテゴリー
    author: Optional[str] # 著者
    updated: Optional[datetime] # 更新日時
```

### 設定検証
起動時に設定ファイルとAPIキーの妥当性を自動検証し、エラーを事前に防ぎます。

## 📊 コスト分析

実行ごとに以下の情報を記録：
- 入力/出力/思考トークン数
- USD/JPY換算での料金
- モデル別の詳細コスト

## 🧪 開発・テスト

### テスト実行
```bash
pytest
```

### 開発依存関係
```bash
pip install -r requirements-dev.txt
```

## 🚧 開発状況

このプロジェクトは**個人の学習記録自動化**を目的とした開発中のツールです。
現在の実装は基本機能のプロトタイプ段階で、多くの改善点があります。

### 既知の課題
- ハードコードされたファイルパス
- 単一ファイル処理のみ
- Claude形式以外未対応
- エラーハンドリング不十分

## 📝 ライセンス

個人プロジェクト（開発中）
