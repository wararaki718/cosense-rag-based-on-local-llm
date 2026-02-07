FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files and shared directory
COPY api-embedding/pyproject.toml .
COPY shared /shared

# Sync dependencies
RUN uv sync --no-dev

# Copy source code
COPY api-embedding/main.py .

EXPOSE 8001

CMD ["uv", "run", "main.py"]
