FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files and shared directory for local install
COPY api-search/pyproject.toml .
COPY shared /shared

# Sync dependencies (including local shared package)
RUN uv sync --no-dev

# Copy source code
COPY api-search/main.py .

EXPOSE 8002

CMD ["uv", "run", "main.py"]
