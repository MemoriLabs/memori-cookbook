# Memori Hosted Chatbot Demo 🧠

A production-ready example of adding long-term memory to an AI chatbot using [Memori's hosted service](https://memorilabs.ai). No database setup required - just three lines of code to add memory!

This cookbook example demonstrates best practices for integrating Memori with FastAPI and OpenAI, following [AGENTS.md](AGENTS.md) principles for maintainable, production-ready code.

## ✨ Features

- 🧠 **Automatic Memory** - AI remembers conversations across sessions
- 🔒 **User Isolation** - Memories are isolated per user ID
- 🎭 **Multiple Agent Types** - General, Programming, Customer Support, Finance
- 🚫 **No Database Setup** - All memory handled by Memori's hosted service
- ⚡ **Zero Added Latency** - Memory retrieval and storage happen in the background
- 🎯 **Three Lines of Code** - That's all it takes to add memory

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [OpenAI API key](https://platform.openai.com/api-keys)
- [Memori API key](https://app.memorilabs.ai/signup) (free!)

### Installation

```bash
# Clone the repository
git clone https://github.com/MemoriLabs/memori-cookbook.git
cd memori-cookbook/examples/hosted-chatbot

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
MEMORI_API_KEY=mk-your-memori-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Run the Server

```bash
# Using the convenience script
python run.py

# Or directly
python -m app.main
```

The server will start at `http://localhost:8000`

- 📚 API Docs: http://localhost:8000/docs
- 🏥 Health Check: http://localhost:8000/health

## 💬 Usage

### Basic Chat Request

```bash
curl -X POST "http://localhost:8000/api/v1/chat/user-123" \
  -H "Content-Type: application/json" \
  -d '{"q": "My favorite color is blue", "name": "Ryan"}'
```

Response:
```json
{
  "messages": [
    {
      "content": "Got it! I'll remember that your favorite color is blue.",
      "role": "assistant"
    }
  ],
  "agent_type": "general"
}
```

### Memory in Action

Ask again in a new request:

```bash
curl -X POST "http://localhost:8000/api/v1/chat/user-123" \
  -H "Content-Type: application/json" \
  -d '{"q": "What is my favorite color?"}'
```

Response:
```json
{
  "messages": [
    {
      "content": "Your favorite color is blue!",
      "role": "assistant"
    }
  ],
  "agent_type": "general"
}
```

**🎉 The AI remembered!** Try it with different user IDs to see memory isolation.

### Using Different Agent Types

```bash
# Programming expert
curl -X POST "http://localhost:8000/api/v1/chat/user-123" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "How do I implement a binary search tree?",
    "agent_type": "programming"
  }'

# Customer support
curl -X POST "http://localhost:8000/api/v1/chat/user-456" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "I need help with my order",
    "agent_type": "customer_support"
  }'
```

### Get Available Agent Types

```bash
curl http://localhost:8000/api/v1/agents
```

## 🏗️ Architecture

### How It Works

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /chat/{user_id}
       ▼
┌──────────────────────────┐
│   FastAPI Endpoint       │
│   (app/api/v1/chat.py)   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   LLM Service            │
│   (app/services/llm.py)  │
│                          │
│   1. Set attribution     │◄──── User ID isolation
│   2. Get system prompt   │◄──── Agent type
│   3. Call OpenAI         │◄──── Memori wraps this!
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Memori (Hosted)        │
│                          │
│   • Retrieves memories   │◄──── Semantic search
│   • Augments context     │◄──── Zero latency
│   • Stores new memories  │◄──── Background process
└──────────────────────────┘
```

### The Magic: Three Lines of Code

This is all it takes to add memory to your AI app:

```python
from memori import Memori

# 1. Wrap your LLM client with Memori
mem = Memori().openai.register(openai_client)

# 2. Set who this conversation is for
mem.attribution(entity_id="user-123", process_id="chat")

# 3. Use your client normally - Memori handles the rest!
response = openai_client.chat.completions.create(...)
```

That's it! Memori automatically:
- ✅ Retrieves relevant memories before the LLM call
- ✅ Augments the context with memory
- ✅ Extracts and stores new memories after the response
- ✅ All with zero added latency to your API response

## 📁 Project Structure

```
hosted-chatbot/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependency injection
│   │   └── v1/
│   │       ├── api.py           # Router aggregation
│   │       └── endpoints/
│   │           ├── agents.py    # Agent types endpoint
│   │           ├── chat.py      # Main chat endpoint
│   │           └── health.py    # Health check
│   ├── core/
│   │   └── config.py            # Configuration management
│   ├── models/
│   │   ├── agents.py            # Agent type models
│   │   └── chat.py              # Request/response models
│   ├── services/
│   │   └── llm.py               # LLM service with Memori
│   ├── main.py                  # FastAPI app factory
│   └── prompts.py               # Agent system prompts
├── tests/
│   └── api/v1/
│       └── test_chat.py         # Endpoint tests
├── .env.example                 # Environment template
├── pyproject.toml               # Project dependencies
├── run.py                       # Quick start script
└── README.md                    # This file
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/api/v1/test_chat.py -v
```

All tests use mocks - no real API calls needed!

## 🎯 Key Design Decisions

This example follows [AGENTS.md](AGENTS.md) best practices:

### 1. **LLM Provider Agnostic**
The model is configurable via environment variables:
```python
# config.py
openai_model: str = "gpt-4o-mini"
```

Switch models easily: `OPENAI_MODEL=gpt-4o`

### 2. **Proper Logging**
Production-ready logging instead of print statements:
```python
import logging
logger = logging.getLogger(__name__)

logger.error(f"Error in chat: {e}", exc_info=True)
```

### 3. **Performance Awareness**
Each chat request makes:
- **1 OpenAI API call** (unavoidable)
- **0 added latency** from Memori (background processing)

### 4. **Clean Error Handling**
Meaningful exceptions with context:
```python
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Error processing chat request: {str(e)}"
    )
```

### 5. **Dependency Injection**
Clean service management via FastAPI:
```python
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
```

## 🔧 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *Required* | Your OpenAI API key |
| `MEMORI_API_KEY` | *Required* | Your Memori API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | `localhost:3000,localhost:5173` | Allowed CORS origins |

## 🎭 Agent Types

| Type | Description | Use Case |
|------|-------------|----------|
| `general` | General purpose assistant | Default, wide range of topics |
| `programming` | Expert programming assistant | Code, debugging, best practices |
| `customer_support` | Professional support agent | Issue resolution, empathy |
| `finance` | Personal finance advisor | Budgeting, investing, planning |

## 📚 Learn More

- **Memori Documentation**: https://memorilabs.ai/docs
- **API Reference**: https://docs.memorilabs.ai/api
- **More Examples**: https://github.com/MemoriLabs/memori-cookbook
- **Discord Community**: https://discord.gg/memori

## 🤝 Contributing

This is a cookbook example! Contributions are welcome:

1. Follow [AGENTS.md](AGENTS.md) principles
2. Add tests for new features
3. Update documentation
4. Keep changes focused and minimal

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 💡 Tips & Tricks

### Switching LLM Providers

While this example uses OpenAI, Memori works with any LLM provider:

```python
# Anthropic
from anthropic import Anthropic
anthropic_client = Anthropic(api_key="...")
mem = Memori().anthropic.register(anthropic_client)

# Or any OpenAI-compatible API
custom_client = OpenAI(base_url="https://your-api.com")
mem = Memori().openai.register(custom_client)
```

### Memory Isolation Strategies

```python
# Per-user memories
mem.attribution(entity_id=user_id, process_id="chat")

# Per-conversation threads
mem.attribution(entity_id=user_id, process_id=f"thread-{thread_id}")

# Per-agent type (already implemented!)
mem.attribution(entity_id=user_id, process_id=f"demo-{agent_type}")
```

### Debugging Memory

Enable debug mode to see what Memori is doing:

```bash
DEBUG=true python run.py
```

Check logs for memory retrieval and storage operations.

## 🎉 What's Next?

Now that you've seen how simple it is to add memory, try:

1. **Frontend Integration** - Build a chat UI using the API
2. **Custom Agent Types** - Add your own specialized agents
3. **Memory Analytics** - Query and visualize stored memories
4. **Multi-Modal** - Add image/file support to conversations

Check out other examples in the [Memori Cookbook](https://github.com/MemoriLabs/memori-cookbook)!
