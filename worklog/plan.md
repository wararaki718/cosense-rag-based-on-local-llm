## Plan: Data Flow & API Contract Design

Tech-Lead として、疎結合でスケーラブルなRAGシステムのためのデータフローと、各サービス間の型定義（Pydantic）の方針を設計します。

### Steps

1. **Define Shared Schema**: `shared/models.py` に、サービス間でやり取りする `ScrapboxChunk`, `SearchResult`, `LLMRequest` などの共通 Pydantic モデルを定義します。
2. **Batch Ingestion Flow**: batch サービスが Scrapbox からデータを取得し、api-embedding でベクトル化後、api-search (Elasticsearch) へ登録するフローを確定します。
3. **Query Pipeline Flow**: frontend がトリガーとなり、api-search でのハイブリッド検索と api-llm での回答生成を統合するシーケンスを設計します。
4. **API Endpoints Design**: 各サービスの `/docs` (OpenAPI) の要件を定義し、api-embedding, api-search, api-llm の主要エンドポイントを策定します。

### Further Considerations

1. **Orchestration**: フロントエンドで全APIを統合するか、バックエンドに軽量なオーケストレータ（BFF）を置くか。現状は frontend が責務を負う設計とします。
2. **Search Logic**: api-search が自ら api-embedding を呼び出すか、呼び出し側がベクトルを渡すか。関心の分離のため、api-search 内でベクトル変換を完結させる構成を推奨します。
3. **Async Processing**: 大量の Scrapbox データのベクトル化を効率化するため、batch からの要求を `asyncio.gather` で並列化しスループットを確保します。
