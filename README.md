[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

<p align="center">
  <strong>Official Cookbook for the Memori Python SDK</strong>
</p>

<p align="center">
  <i>Practical examples and tutorials for adding persistent memory to your AI applications.</i>
</p>

<p align="center">
  <a href="https://opensource.org/license/apache-2-0">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  </a>
  <a href="https://discord.gg/abD4eGym6v">
    <img src="https://img.shields.io/discord/1042405378304004156?logo=discord" alt="Discord">
  </a>
</p>

<p align="center">
  <a href="https://github.com/MemoriLabs/memori-cookbook/stargazers">
    <img src="https://img.shields.io/badge/Star%20the%20Cookbook-Support%20the%20project-orange?style=for-the-badge" alt="Star the Cookbook">
  </a>
</p>

---

## What is Memori?

Memori is a Python SDK that adds persistent memory to any LLM application. With just a few lines of code, your AI can remember conversations, user preferences, and context across sessions.

```python
from openai import OpenAI
from memori import Memori

client = OpenAI(...)
mem = Memori().openai.register(client)
```

For full SDK documentation, visit the [Memori SDK Repository](https://github.com/MemoriLabs/Memori).

---

## Quick Start

### Installation

```bash
# Install uv (if you haven't already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the cookbook
git clone https://github.com/MemoriLabs/memori-cookbook.git
cd memori-cookbook

# Install dependencies
uv sync
```

---

## Development

### Setup

```bash
# Install development dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Resources

- **Memori SDK**: [https://github.com/MemoriLabs/Memori](https://github.com/MemoriLabs/Memori)
- **Documentation**: [https://memorilabs.ai/docs](https://memorilabs.ai/docs)
- **API Reference**: [https://memorilabs.ai/docs/api](https://memorilabs.ai/docs/api)

---

## Support

- **Discord**: [https://discord.gg/abD4eGym6v](https://discord.gg/abD4eGym6v)
- **Issues**: [GitHub Issues](https://github.com/MemoriLabs/memori-cookbook/issues)
- **SDK Issues**: [Memori SDK Issues](https://github.com/MemoriLabs/Memori/issues)

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

**Star us on GitHub** to support the project
