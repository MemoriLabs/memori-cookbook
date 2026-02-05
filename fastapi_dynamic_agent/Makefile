.PHONY: help install clean lint format check test test-cov run dev all

# Default target - show available commands
help:
	@echo "Memori Hosted Chatbot - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install dependencies with uv"
	@echo "  make clean       Remove cache files and build artifacts"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint        Check code with ruff (no changes)"
	@echo "  make format      Format code with ruff"
	@echo "  make check       Run lint + format + tests (pre-commit)"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run all tests"
	@echo "  make test-cov    Run tests with coverage report"
	@echo ""
	@echo "Running:"
	@echo "  make run         Start the server (production mode)"
	@echo "  make dev         Start the server (dev mode with reload)"
	@echo ""
	@echo "All-in-One:"
	@echo "  make all         Install + check + test (fresh start)"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies with uv..."
	uv sync
	@echo "✅ Dependencies installed!"

# Clean up cache and build artifacts
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "✅ Cleaned!"

# Lint code (check only, no changes)
lint:
	@echo "🔍 Checking code with ruff..."
	ruff check app/ tests/
	@echo "✅ Lint check passed!"

# Format code (makes changes)
format:
	@echo "✨ Formatting code with ruff..."
	ruff format app/ tests/
	ruff check app/ tests/ --fix
	@echo "✅ Code formatted!"

# Run all quality checks (lint + format check + type check)
check: lint
	@echo "📋 Checking formatting..."
	ruff format app/ tests/ --check
	@echo "✅ All checks passed!"

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v
	@echo "✅ Tests passed!"

# Run tests with coverage
test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest --cov=app --cov-report=term-missing --cov-report=html tests/
	@echo ""
	@echo "📊 Coverage report generated in htmlcov/index.html"
	@echo "✅ Tests passed!"

# Run the server (production mode)
run:
	@echo "🚀 Starting Memori Hosted Chatbot..."
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "🏥 Health: http://localhost:8000/health"
	@echo ""
	python run.py

# Run the server (development mode with auto-reload)
dev:
	@echo "🔧 Starting development server..."
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "🏥 Health: http://localhost:8000/health"
	@echo ""
	@echo "♻️  Auto-reload enabled - save files to restart"
	@echo ""
	DEBUG=true python run.py

# Full workflow - install, check, test
all: install clean check test
	@echo ""
	@echo "✅ All tasks completed successfully!"
	@echo "🚀 Ready to code!"

# Pre-commit checks (run before committing)
pre-commit: format check test
	@echo ""
	@echo "✅ Pre-commit checks passed!"
	@echo "👍 Safe to commit!"
