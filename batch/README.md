# batch

Data Ingestion service for Scrapbox RAG.

## Responsibilities
- Fetch pages from Scrapbox API.
- Semantic chunking (based on indents and empty lines).
- Coordinate with `api-embedding` and `api-search` to index data.

## Setup
```bash
uv sync
```

## Usage
```bash
# Example: Index a public project
export SCRAPBOX_PROJECT=project-name
uv run main.py
```

## Environment Variables
- `SCRAPBOX_PROJECT`: Target project name.
- `SCRAPBOX_SID`: (Optional) Connect.sid for private projects.
- `EMBEDDING_API_URL`: default `http://localhost:8001`
- `SEARCH_API_URL`: default `http://localhost:8002`
