# Customer Support AI Agent with DigitalOcean's Gradient AI platform and Memori

A powerful, embeddable AI customer support solution that can be integrated into any website with a single JavaScript snippet. Built using [DigitalOcean's Gradient AI platform](https://www.digitalocean.com/products/gradient/platform) for AI agent capabilities and [Memori](https://github.com/MemoriLabs/Memori) for persistent conversation memory with automatic context recall.

## 📚 Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - Complete system architecture, data flows, and component responsibilities
- **[Quick Reference](QUICK_REFERENCE.md)** - Fast API reference for common operations

## Features

- 🤖 **AI-Powered Support**: Uses DigitalOcean's Gradient AI platform for contextual understanding
- 🧠 **Persistent Memory with Memori**: Direct database integration for conversation memory, automatic fact extraction, and semantic search
- 🕷️ **Knowledge Base Management**: File uploads, text content, and URL scraping for context-aware responses
- 💾 **Persistent Storage**: Agents and knowledge bases stored in PostgreSQL with automatic synchronization
- 🚀 **Easy Integration**: Single JavaScript snippet for any website
- 🐳 **Docker Ready**: Complete containerized setup with docker-compose
- 🔒 **Domain-Based Security**: Per-domain memory isolation via X-Domain-ID headers
- 🎨 **Customizable Widget**: Configurable appearance and behavior
- ⚡ **Non-Blocking Deployment**: Background agent deployment with instant user feedback
- 🔄 **Automatic Context Recall**: Memori automatically recalls relevant facts from previous conversations

## Architecture

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Website       │    │   FastAPI        │    │   PostgreSQL    │
│   + Widget.js   │◄──►│   Backend        │◄──►│   (Persistence) │
│                 │    │                  │    │   • Agents      │
└─────────────────┘    └──────────────────┘    │   • KBs         │
                                │              │   • Sessions    │
                                │              │   • Memori      │
                    ┌───────────┼───────────┐  └─────────────────┘
                    │           │           │
                    ▼           ▼           ▼
         ┌──────────────┐  ┌────────────┐  ┌──────────────┐
         │ DigitalOcean │  │   Memori   │  │  Knowledge   │
         │  Gradient AI │  │  (Direct   │  │  Bases (DO)  │
         │   (Agents)   │  │Integration)│  │              │
         └──────────────┘  └────────────┘  └──────────────┘
```

**Key Components**:
- **DigitalOcean Client** (`digitalocean_client.py`) - Agent & KB management, access key creation
- **Memori Integration** (`memori_integration.py`) - Direct Memori integration with DigitalOcean Gradient AI agents, automatic memory management
- **Knowledge Uploader** (`knowledge_upload.py`) - File processing and knowledge base population
- **Domain-Based Isolation** - Per-domain memory isolation via X-Domain-ID headers

## What's New: Memori Integration

This version uses Memori with direct database integration:

- **DigitalOcean Gradient AI Integration**: Memori wraps the Gradient AI agent for automatic memory capture
- **No Additional API Keys**: Uses your existing DigitalOcean Gradient AI agent credentials
- **Automatic Context Recall**: Relevant facts are automatically added to conversations
- **Advanced Augmentation**: Facts are extracted in the background with zero latency impact
- **Entity & Process Attribution**: Memories are attributed to users (entities) and agents (processes)
- **Semantic Search**: Built-in vector search for recalling relevant conversation history
- **Direct Database**: All memory stored in your PostgreSQL database

## Quick Start

### Prerequisites

- Docker and Docker Compose
- DigitalOcean API token with Gradient AI access
- Python 3.11+ (for local development)

### 1. Clone and Configure

```bash
git clone https://github.com/MemoriLabs/customer-support-agent-memory.git
cd customer-support-agent-memori

# Update your configuration in .env file
cp .env.example .env
# Edit .env and add:
# - DIGITALOCEAN_TOKEN
# - Database credentials
```

### 2. Start with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`

### 3. Test the Integration

Open `http://localhost:8000/static/demo.html` to see the widget in action.

## Manual Setup (Development)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup PostgreSQL

```bash
# Install PostgreSQL
# On macOS with Homebrew:
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database and user
createdb customer_support
psql customer_support < init.sql

# Memori will automatically create its schema on first run
```

### 3. Configure Environment

```bash
# Copy and edit environment variables
cp .env.example .env
# Edit .env with your:
# - Database credentials
# - DigitalOcean API settings
```

### 4. Run the Application

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Integration Guide

### Basic Integration

Add this to your website's HTML:

```html
<!-- Include the widget script -->
<script src="http://localhost:8000/static/widget.js" data-domain-id="your-domain-id"></script>
```

## API Endpoints

For complete API documentation, see [QUICK_REFERENCE.md](QUICK_REFERENCE.md).

### Domain Registration

#### Register Domain
```http
POST /register-domain
Content-Type: application/json
Authorization: Bearer YOUR_ADMIN_API_KEY

{
    "domain_name": "example.com"
}
}

Response:
{
    "domain_id": "uuid-here",
    "api_key": "generated-api-key",
    "message": "Domain registered successfully"
}
```

### Session Management

#### Start Session
```http
POST /session
Content-Type: application/json
X-Domain-ID: your-domain-id

{
    "user_id": "user123",
    "website_url": "https://example.com" (optional)
}
```

### Chat

#### Ask Question
```http
POST /ask
Content-Type: application/json
X-Domain-ID: your-domain-id

{
    "question": "How do I reset my password?",
    "session_id": "uuid-here",
    "user_id": "user123"
}
```

### Knowledge Base Management

#### Upload File (PDF, TXT, MD, JSON, CSV)
```http
POST /knowledge/upload/file
Content-Type: multipart/form-data
X-Domain-ID: your-domain-id

Form data:
- website_url: "https://example.com"
- file: [binary file data]
- chunk_size: 1000 (optional)
- use_semantic: false (optional)
- custom_name: "Custom Document Name" (optional)

Supported file types:
- PDF (.pdf) - Extracts text from PDF documents
- Text (.txt) - Plain text files
- Markdown (.md) - Markdown documents with formatting
- JSON (.json) - Structured JSON data
- CSV (.csv) - Tabular data from CSV files
```

#### Upload Text Content
```http
POST /knowledge/upload/text
Content-Type: application/json
X-Domain-ID: your-domain-id

{
    "website_url": "https://example.com",
    "text_content": "Your plain text content here...",
    "document_name": "My Document",
    "chunk_size": 1000,
    "use_semantic": false
}
```

#### Upload from URL
```http
POST /knowledge/upload/url
Content-Type: application/json
X-Domain-ID: your-domain-id

{
    "website_url": "https://example.com",
    "url_to_scrape": "https://docs.example.com",
    "max_depth": 2,
    "max_links": 20,
    "chunk_size": 1000
}
```

#### Get Supported File Types
```http
GET /knowledge/supported-types
X-Domain-ID: your-domain-id

Response:
{
    "supported_types": [".pdf", ".txt", ".md", ".json", ".csv"],
    "descriptions": {
        ".pdf": "PDF documents",
        ".txt": "Plain text files",
        ".md": "Markdown documents",
        ".json": "JSON data files",
        ".csv": "CSV data files"
    },
    "additional_sources": ["url", "text"]
}
```

### Website Scraping

#### Scrape Website (Manual)
```http
POST /scrape
Content-Type: application/json
X-Domain-ID: your-domain-id

{
    "website_url": "https://example.com",
    "max_depth": 2,
    "max_links": 20
}
```

**Note**: Widget no longer auto-scrapes. Use this endpoint manually to populate knowledge base.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DIGITALOCEAN_TOKEN` | DigitalOcean API token (required) | - |
| `DIGITALOCEAN_AGENT_NAME` | Agent name prefix | `customer-support` |
| `DIGITALOCEAN_KNOWLEDGE_BASE_NAME` | KB name prefix | `website-kb` |
| `DIGITALOCEAN_AGENT_INSTRUCTIONS` | Agent instructions | Custom instructions |
| `DIGITALOCEAN_MODEL` | AI model to use | `deepseek-ai/DeepSeek-V3` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `customer_support` |
| `POSTGRES_USER` | Database user | `do_user` |
| `POSTGRES_PASSWORD` | Database password | `do_user_password` |

## Database Schema

The system automatically creates the following tables:

### Core Tables
- `registered_domains` - Domain registration and identification
- `user_sessions` - Manages user sessions with status tracking
- `agents` - Stores DigitalOcean agent metadata and access keys (domain-based)
- `knowledge_bases` - Tracks knowledge base UUIDs and website associations
- `conversation_history` - Stores chat history per session

### Agent Persistence
```sql
-- Registered domains
CREATE TABLE registered_domains (
    id UUID PRIMARY KEY,
    domain_name TEXT UNIQUE NOT NULL,      -- Base domain (e.g., "example.com")
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agents table stores DigitalOcean agent information
CREATE TABLE agents (
    website_key TEXT PRIMARY KEY,          -- Hash of domain_name
    agent_uuid UUID NOT NULL,
    agent_url TEXT NOT NULL,
    agent_access_key TEXT,                 -- Fresh API key (32 chars)
    knowledge_base_uuids TEXT[],
    website_url TEXT,                      -- Normalized as https://{domain_name}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge Bases table stores KB metadata
CREATE TABLE knowledge_bases (
    website_key TEXT PRIMARY KEY,
    kb_uuid UUID NOT NULL,
    website_url TEXT NOT NULL,
    kb_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Monitoring

Check stored resources:

```sql
-- View all registered domains
SELECT id, domain_name, created_at
FROM registered_domains
ORDER BY created_at DESC;

-- View all agents with their domains
SELECT a.website_key, a.agent_uuid, a.website_url, a.agent_access_key IS NOT NULL as has_key, a.created_at
FROM agents a
ORDER BY a.created_at DESC;

-- View all knowledge bases
SELECT website_key, kb_uuid, website_url, kb_name
FROM knowledge_bases
ORDER BY created_at DESC;

-- Count resources
SELECT
    (SELECT COUNT(*) FROM registered_domains) as total_domains,
    (SELECT COUNT(*) FROM agents) as total_agents,
    (SELECT COUNT(*) FROM knowledge_bases) as total_kbs,
    (SELECT COUNT(*) FROM user_sessions WHERE status = 'active') as active_sessions;

-- Check agent access keys
SELECT website_key,
       agent_uuid,
       LENGTH(agent_access_key) as key_length,
       agent_access_key IS NOT NULL as has_key
FROM agents;
```

## Production Deployment

### Security Considerations

1. **API Keys**: Store DigitalOcean token securely
2. **CORS**: Configure allowed origins properly
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **SSL**: Use HTTPS in production
5. **Database**: Secure PostgreSQL with proper authentication
6. **Agent Access Keys**: Stored securely in database, encrypted at rest

### Scaling

1. **Database**: Use managed PostgreSQL service (DigitalOcean's Fully Managed PostgreSQL)
2. **API**: Deploy behind load balancer
3. **Caching**: Implement Redis for session caching
4. **CDN**: Serve widget.js from CDN

### Monitoring

Monitor these metrics:
- API response times
- Database performance (check `agents` and `knowledge_bases` tables)
- Session creation rate
- DigitalOcean API usage and quotas
- Error rates
- Memory cache hit/miss rates

## Troubleshooting

For detailed troubleshooting, see [ARCHITECTURE.md - Troubleshooting Section](ARCHITECTURE.md#troubleshooting--known-issues).

### Common Issues

1. **Widget not appearing**
   - Check console for JavaScript errors
   - Verify API URL is correct
   - Ensure CORS is configured properly
   - Verify X-Domain-ID header is set correctly

2. **401 Unauthorized errors**
   - **Fixed**: Access keys now created fresh via POST /agents/{uuid}/api_keys
   - Verify domain is registered: Check `registered_domains` table
   - Ensure X-Domain-ID header matches registered domain ID
   - Check agent has valid access key: `SELECT agent_access_key FROM agents WHERE website_key = '...'`

3. **Duplicate agents created**
   - **Fixed**: Now uses domain_name from registered_domains for consistent website_key
   - Single agent per registered domain regardless of URL variations (www vs non-www)
   - Query: `SELECT * FROM agents WHERE website_url LIKE '%example.com%'`

4. **Knowledge base 404 errors**
   - **Fixed**: KBs now attached after agent deployment completes
   - Background polling waits for STATUS_RUNNING before attaching KBs
   - Check agent status: Look for "Background polling completed" in logs

5. **Database connection errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Verify user permissions (do_user)
   - Ensure all required tables exist (run init.sql if needed)

6. **DigitalOcean API errors**
   - Verify DIGITALOCEAN_TOKEN is valid
   - Check account access to Gradient AI
   - Monitor API rate limits
   - Check agent and KB creation logs for specific error messages

7. **Memori integration issues**
   - Memori now uses direct database integration (no API keys)
   - Verify PostgreSQL connection is working
   - Check that Memori tables are created automatically
   - Monitor logs for Memori initialization messages

8. **Widget not auto-scraping**
   - **By design**: Auto-scraping removed for performance
   - Use manual `/scrape` endpoint to populate knowledge base
   - Or upload files via `/knowledge/upload/*` endpoints

### Code Structure

```
├── main.py                      # FastAPI application with all endpoints
├── digitalocean_client.py       # DigitalOcean Gradient AI client
│                                #   - Agent creation & management
│                                #   - Knowledge base operations
│                                #   - Access key creation (POST /api_keys)
├── memori_client.py             # Memori API client (domain-specific memory)
│                                #   - MemoriClient class
│                                #   - Async chat() and get_context() methods
├── knowledge_upload.py          # Knowledge base file upload handler
├── memori_tool.py               # Memori tool integration (legacy)
├── auth.py                      # Authentication utilities
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Docker services configuration
├── Dockerfile                   # API container definition
├── init.sql                     # Database initialization schema
├── Procfile                     # Heroku deployment configuration
├── .env                         # Environment variables (not in repo)
├── ARCHITECTURE.md              # 📚 Complete system architecture
├── QUICK_REFERENCE.md           # 📘 API quick reference guide
├── README.md                    # This file
├── static/
│   ├── widget.js                # Embeddable widget (no auto-scrape)
│   ├── demo.html                # Integration demo page
│   └── knowledge_upload_demo.html # KB upload demo
└── __pycache__/                 # Python bytecode cache
```

**Key Files**:
- **main.py**: Core FastAPI app with domain registration, session management, chat, and knowledge endpoints
- **digitalocean_client.py**: Handles all DigitalOcean API interactions including agent/KB creation and access key management
- **memori_client.py**: Dedicated module for Memori API integration with per-domain memory isolation
- **knowledge_upload.py**: Processes file uploads (PDF, TXT, MD, JSON, CSV) and URL scraping
- **widget.js**: Client-side embeddable widget (updated to remove auto-scraping)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs`
