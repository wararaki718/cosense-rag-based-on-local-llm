FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files (from service dir)
COPY api-embedding/pyproject.toml .

# Sync dependencies
RUN uv sync --no-dev

# Copy source code and shared models
COPY api-embedding/main.py .
COPY shared /app/shared

# Ensure shared is in PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uv", "run", "main.py"]
