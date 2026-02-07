# Scrapbox RAG Project Makefile

.PHONY: help setup up down ps logs build ingest frontend-dev lint lint-fix

help: ## Show help messages
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies for all services locally (uv and npm)
	@echo "Installing backend dependencies..."
	cd api-embedding && uv sync
	cd api-search && uv sync
	cd api-llm && uv sync
	cd batch && uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

build: ## Build docker images
	docker compose build

up: ## Start all services in background
	docker compose up -d

down: ## Stop all services
	docker compose down

ps: ## Check service status
	docker compose ps

logs: ## Show logs
	docker compose logs -f

ingest: ## Run batch ingestion (Usage: make ingest project=PROJECT_NAME [sid=SID])
	@if [ -z "$(project)" ]; then \
		echo "Error: project is required. Usage: make ingest project=your-project [sid=your-sid]"; \
		exit 1; \
	fi
	cd batch && SCRAPBOX_PROJECT=$(project) SCRAPBOX_SID=$(sid) uv run main.py

frontend-dev: ## Run frontend in development mode locally
	cd frontend && npm run dev

api-embedding-dev: ## Run embedding API locally (with MPS acceleration)
	cd api-embedding && uv run main.py

api-search-dev: ## Run search API locally
	cd api-search && uv run main.py

api-llm-dev: ## Run LLM API locally
	cd api-llm && uv run main.py

lint: ## Run linter checks (Ruff)
	uv run ruff check .

lint-fix: ## Run linter and apply automatic fixes
	uv run ruff check . --fix
