# Memori Contributor Assistant CLI

A command-line assistant to help developers contribute to Memori. Built with **Memori v3** and supports **multi-LLM providers** (OpenAI, Anthropic, Gemini, xAI).

## Features

- **Multi-LLM Support**: Works with OpenAI, Anthropic, Gemini, and xAI
- **Persistent Memory**: Remembers your goals and preferences across sessions
- **Developer-Focused**: Helps with bug fixes, features, and documentation
- **Context-Aware**: Learns your coding style and project preferences
- **Local Storage**: All data stored locally in SQLite (`~/.memori_contributor/`)

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- At least one LLM API key:
  - OpenAI API key (for GPT-4o-mini)
  - Anthropic API key (for Claude)
  - Google Gemini API key
  - xAI API key (for Grok)

## Installation

### Step 1: Activate Python Environment

You need an active Python environment to install and use the CLI. Choose one option:

**Option A: Use existing Memori virtual environment** (if you already have Memori installed)

```bash
source ~/Documents/GitHub/memori/venv/bin/activate
```

**Option B: Create a new virtual environment for this project**

```bash
cd contributor_assistant_cli
python3.12 -m venv venv
source venv/bin/activate
```

### Step 2: Install the Package

Once your virtual environment is activated, install the contributor assistant:

**Using pip (Recommended)**

```bash
cd contributor_assistant_cli
pip install -e .
```

**Using uv**

```bash
cd contributor_assistant_cli
uv sync
```

### Step 3: Verify Installation

Check that the CLI is available:

```bash
which contributor-assistant
contributor-assistant --help
```

You should see the help menu with available commands.

### Step 4: Setup API Keys

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Add your API keys to `.env`:
```bash
# For Anthropic (recommended for this guide)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Or for OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here

# Or for Gemini
GEMINI_API_KEY=your-google-api-key-here

# Or for xAI
XAI_API_KEY=xai-your-api-key-here
```

## Usage

### First Time Setup

Initialize the assistant with your preferences:

```bash
contributor-assistant init
```

You'll be prompted to select:
- Your contribution type (bug fixes, features, documentation)
- Your areas of interest (adapters, storage, testing, etc.)
- Your preferred LLM provider

### Ask Questions

Ask the assistant about contributing to Memori:

```bash
# Basic question
contributor-assistant ask "How do I set up Memori for development?"

# Override provider
contributor-assistant --provider openai ask "What's the project structure?"

# Another question (memory persists!)
contributor-assistant ask "What coding style should I follow?"
```

### Check Your Context

View your stored memories and configuration:

```bash
contributor-assistant context
```

Output shows:
- Your entity ID and process info
- Contribution type and areas of interest
- Stored facts from previous conversations

### Switch LLM Provider

Change your default LLM provider:

```bash
contributor-assistant provider
```

### Reset Everything

Clear all memories and configuration (careful!):

```bash
contributor-assistant reset
```

## Project Structure

```
contributor_assistant_cli/
├── cli.py                 # Click CLI interface with all commands
├── core.py                # ContributorAssistant main logic
├── llm_manager.py         # Multi-LLM provider abstraction
├── memory_manager.py      # Memori integration and persistence
├── config.py              # Configuration management
├── pyproject.toml         # Project dependencies and metadata
├── requirements.txt       # For pip users
├── README.md              # This file
└── .env.example           # API key template
```

## How It Works

### Architecture

```
┌─────────────────┐
│    CLI Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Config Manager     │ ◄──► ~/.memori_contributor/config.json
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐       ┌──────────────────┐
│ ContributorAssistant│       │  LLMManager      │
├─────────────────────┤       ├──────────────────┤
│ • Core Logic        │ ◄────►│ • OpenAI         │
│ • System Prompt     │       │ • Anthropic      │
│ • Context Building  │       │ • Gemini         │
└────────┬────────────┘       │ • xAI            │
         │                    └──────────────────┘
         ▼
┌──────────────────────────┐
│  MemoryManager + Memori  │
├──────────────────────────┤
│ • Registers LLM Client   │
│ • Persists Memory        │
│ • Tracks Conversations   │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  SQLite Database         │
├──────────────────────────┤
│ ~/.memori_contributor/   │
│ memori.db                │
│                          │
│ Tables:                  │
│ • memori_entity_fact     │
│ • memori_conversation    │
│ • memori_knowledge_graph │
└──────────────────────────┘
```

### Memory Flow

1. **Initialize**: You set up your contribution goals and LLM provider
2. **Ask**: When you ask a question, it's sent to the chosen LLM
3. **Persist**: Memori automatically captures the conversation and extracts facts
4. **Remember**: On the next question, Memori provides context about your previous interactions
5. **Improve**: Claude gives increasingly personalized advice as it learns about your goals

### What Gets Stored

- Your contribution type (bug fixes, features, docs)
- Your areas of interest (adapters, storage layer, etc.)
- Facts extracted from conversations:
  - "Developer interested in Anthropic adapter"
  - "Developer prefers type-hinted code"
  - "Developer wants to work on streaming"
- Full conversation history (searchable with Memori)

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | If using OpenAI | - | OpenAI API authentication |
| `ANTHROPIC_API_KEY` | If using Anthropic | - | Anthropic API authentication |
| `GEMINI_API_KEY` | If using Gemini | - | Google Gemini API authentication |
| `XAI_API_KEY` | If using xAI | - | xAI Grok API authentication |
| `MEMORI_API_KEY` | Optional | - | Memori Advanced Augmentation (higher quotas) |

## Example Workflow

```bash
# 1. First time setup
$ contributor-assistant init
Welcome to Memori Contributor Assistant!

What would you like to contribute to Memori?
  1. Bug fixes
  2. New features
  3. Documentation
Choice: 2

Which areas interest you? (comma-separated)
  1. Anthropic adapter
  2. Storage layer
  3. Memory augmentation
  4. Testing patterns
  5. Documentation
  6. Other
Enter numbers: 1,3

✅ Initialized!
Provider: anthropic
Contribution type: new features
Areas: Anthropic adapter, Memory augmentation

# 2. Ask a question
$ contributor-assistant ask "How do I improve streaming support in the Anthropic adapter?"

Using provider: anthropic

🤔 Thinking...
