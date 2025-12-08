.PHONY: help install dev lint format clean setup-hooks pre-commit

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --extra dev

setup-hooks: ## Set up pre-commit hooks
	uv run pre-commit install
	@echo ""
	@echo "Pre-commit hooks installed successfully!"

lint: ## Run linting (format check)
	uv run ruff check .

format: ## Format code
	uv run ruff format .
	uv run ruff check --fix .

clean: ## Clean up Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

pre-commit: ## Run pre-commit on all files
	uv run pre-commit run --all-files
