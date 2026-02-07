FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files and shared directory
COPY api-llm/pyproject.toml .
COPY shared /shared

# Sync dependencies
RUN uv sync --no-dev

# Copy source code
COPY api-llm/main.py .

EXPOSE 8003

CMD ["uv", "run", "main.py"]
