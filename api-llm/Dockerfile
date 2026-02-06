FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY api-llm/pyproject.toml .
RUN uv sync --no-dev

COPY api-llm/main.py .
COPY shared /app/shared

# Ensure shared is in PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 8003

CMD ["uv", "run", "main.py"]
