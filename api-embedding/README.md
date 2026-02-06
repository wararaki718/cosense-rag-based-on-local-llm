# api-embedding

Text to Vector conversion service for Scrapbox RAG.

## Responsibilities
- Convert text chunks into sparse vectors (SPLADE).
- Utilize Apple Silicon MPS (Metal Performance Shaders) for acceleration.
- Provide a single endpoint for vector generation.

## Setup
```bash
uv sync
```

## Environment Variables
- `MODEL_NAME`: Name of the HuggingFace model (default: `naver/splade-cocondenser-ensemblev2`)
- `DEVICE`: `mps` for Apple Silicon, `cpu` otherwise.
