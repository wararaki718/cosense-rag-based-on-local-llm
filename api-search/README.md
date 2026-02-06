# api-search

Search Engine service for Scrapbox RAG.

## Responsibilities
- Proxy for Elasticsearch 8.16.
- Perform hybrid search (BM25 + SPLADE Sparse Vector).
- Manage index creation and mapping.

## Setup
```bash
uv sync
```

## Environment Variables
- `ELASTICSEARCH_URL`: URL of the Elasticsearch instance (default: `http://localhost:9200`)
- `EMBEDDING_API_URL`: URL of the api-embedding service (default: `http://localhost:8001`)
- `INDEX_NAME`: Name of the search index (default: `scrapbox-chunks`)
