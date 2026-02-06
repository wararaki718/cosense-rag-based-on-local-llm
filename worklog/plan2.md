# Plan: Fix Microservices for Docker Orchestration

Tech-Lead として、Docker Compose 環境でアプリケーションが正しく動作し、ブラウザからのリクエストを受け付けられるように修正します。

## Steps

1. **Initialize Shared Package**: `shared/__init__.py` を作成し、共有モデルをパッケージとしてインポート可能にします。
2. **Apply CORS Middleware**: api-embedding, api-search, api-llm に `CORSMiddleware` を追加し、フロントエンドからのブラウザ経由のアクセスを許可します。
3. **Fix Dockerfiles**: root context からのビルドを前提に、Dockerfile などの `COPY` コマンドを修正し、`PYTHONPATH` を設定して shared モジュールを認識させます。
4. **Update Frontend Environment**: page.tsx において、ハードコードされた URL を環境変数 (`process.env.NEXT_PUBLIC_...`) に置き換えます。
5. **Standardize Shared Imports**: 各サービスの `main.py` で定義されている重複したモデルを、`shared.models` からのインポートに統一します。

## Further Considerations

1. **GPU/MPS Acceleration**: Docker コンテナ内での MPS (Metal) 利用は複雑なパススルーが必要なため、今回のプラットフォーム最適化は Python 直上実行を推奨し、Docker はあくまで標準的な CPU 実行用として整備します。
2. **Healthchecks**: compose.yml で api-search が api-embedding の起動を待機するように `healthcheck` を追加し、依存関係の堅牢性を高めます。
