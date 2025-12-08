# Contributing to Memori Cookbook

Thank you for your interest in contributing to the Memori Cookbook!

## Development Setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Quick Start

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/MemoriLabs/memori-cookbook.git
cd memori-cookbook

# Install dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

## Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### Pre-commit Hooks

Pre-commit hooks run automatically on each commit:

```bash
# Install hooks (one-time setup)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

### Code Standards

- Follow PEP 8 standards
- Line length: 88 characters
- Use Python 3.10+ syntax and type hints

## Questions

- [GitHub Issues](https://github.com/MemoriLabs/memori-cookbook/issues) - Bug reports and feature requests
- [Discord](https://discord.gg/abD4eGym6v) - Questions and community
