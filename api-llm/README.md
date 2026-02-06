# api-llm

Inference Engine for Scrapbox RAG using local LLM.

## Responsibilities
- Construct RAG prompts from search context.
- Communicate with local LLM (Ollama / Gemma 3).
- Stream or return generated answers.

## Setup
```bash
uv sync
```

## Environment Variables
- `OLLAMA_URL`: URL of the Ollama API (default: `http://localhost:11434`)
- `MODEL_NAME`: Name of the Gemma 3 model (default: `gemma3:4b`)
