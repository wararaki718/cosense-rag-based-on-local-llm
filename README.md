# Scrapbox RAG System

Scrapboxの知見を統合する、Apple Silicon (M1/M2/M3) 最適化済みのローカル完結型RAGシステムです。

## 🚀 特徴

- **完全ローカル完結**: プライバシーを重視し、すべてのデータ処理と推論をローカル環境で実行します。
- **ハイブリッド検索**: Elasticsearchを使用したキーワード検索(BM25)と、SPLADEによるスパースベクトル検索を組み合わせた高精度な検索。
- **Apple Silicon 最適化**: PyTorchのMPS (Metal Performance Shaders) を活用し、埋め込み生成を高速化。
- **マイクロサービスアーキテクチャ**: 各機能が独立しており、柔軟な拡張や部分的なアップデートが可能です。
- **Gemma 3 対応**: ローカルLLMとしてOllama経由でGemma 3を使用し、コンテキストに基づいた回答を生成。

## 🏗 アーキテクチャ

システムは以下の5つの主要コンポーネントで構成されています：

1.  **frontend**: Next.js (App Router) 製の検索・回答UI。
2.  **api-search**: Elasticsearch 8.16のラッパー。ハイブリッド検索のロジックを保有。
3.  **api-embedding**: テキストをSPLADEスパースベクトルに変換するAPI (MPS加速)。
4.  **api-llm**: RAGプロンプトの構築とOllama (Gemma 3) への問い合わせ。
5.  **batch**: Scrapbox APIからのデータ取得とセマンティックチャンキング、インデックス登録。

## 🛠 セットアップ

### 前提条件
- macOS (Apple Silicon 推奨)
- [Docker](https://www.docker.com/) & Docker Compose
- [Ollama](https://ollama.com/) (Gemma 3 4B モデルをダウンロード済み: `ollama run gemma3:4b`)
- [uv](https://github.com/astral-sh/uv) (Python パッケージマネージャ)

### クイックスタート

1.  **インフラとAPIの起動**:
    ```bash
    make build
    make up
    ```
    ※ 初回起動時は `api-embedding` が約500MB〜1GBのモデル（SPLADE）をダウンロードするため、準備完了まで数分かかります。

2.  **埋め込みAPIのローカル起動 (MPS加速を利用する場合)**:
    ※Docker内ではMPSが利用できないため、ベクトル化を高速に行いたい場合はローカルでの起動を推奨します。その際、`api-search` などの他のサービスは `make up` で起動したままにしてください。
    ```bash
    # batch/main.py の EMBEDDING_API_URL を localhost:8001 に向けて実行
    make api-embedding-dev
    ```

3.  **Scrapboxデータのインデックス**:
    ```bash
    # プロジェクト名 `stacker8` の場合
    make ingest project=stacker8
    ```
    ※ `batch` 処理は、`api-embedding` と `api-search` のヘルスチェックが通るまで自動的に待機します。

4.  **UIへのアクセス**:
    [http://localhost:3000](http://localhost:3000) を開き、質問を入力してください。

## 📖 開発者向けコマンド (Makefile)

| コマンド | 説明 |
| :--- | :--- |
| `make build` | 全サービスのDockerイメージをビルド |
| `make up` | 全サービスをバックグラウンドで起動 |
| `make down` | サービスの停止と削除 |
| `make ingest project=xxx` | Scrapboxデータの取り込み (自動待機・並列制限付き) |
| `make logs` | ログのリアルタイム表示 |
| `make frontend-dev` | フロントエンドのローカル開発モード起動 |
| `make api-embedding-dev` | 埋め込みAPIをMPS加速有効で起動 |

## 📐 技術仕様

### データ処理 (Batch)
- **チャンキング**: インデントレベル、空行、および **1000文字のサイズ制限** に基づいたセマンティックチャンキング。Scrapboxの構造的な文脈を維持しつつ、モデルのコンテキスト制限（512トークン）に最適化。
- **ベクトル化**: `naver/splade_v2_distil` モデルを使用し、30,522次元のスパースベクトルを生成。Pydantic v2 の JSON シリアライズ規約に準拠。

### 検索ロジック (api-search)
- **Elasticsearch Mapping**: `rank_features` フィールドを使用してスパースベクトルを格納。日本語解析には `kuromoji` を使用。
- **Hybrid Query**: BM25 によるテキストマッチングとスパースベクトルによる意味的マッチングを `should` 句で統合。Elasticsearch 8系との完全な通信互換性を確保。

### 推論 (api-llm)
- **Prompt**: 検索結果から得られた上位K個のチャンクをコンテキストとして挿入。
- **Gemma 3**: 日本語対応の Gemma 3 モデルを、温度 0.1 で実行し安定した回答を生成。Ollama API 経由で推論を実行。

## 📄 ライセンス
MIT License
