# Customer Support Agent Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                          │
├─────────────────────────────────────────────────────────────────────┤
│  Web UI Demo  │  cURL/CLI  │  Python Client  │  JavaScript Widget   │
└────────┬────────────┬────────────┬────────────────┬──────────────────┘
         │            │            │                │
         └────────────┴────────────┴────────────────┘
                              │
                    HTTP POST with Bearer Token
                              │
                              ▼
         ┌────────────────────────────────────────────┐
         │         FastAPI Application                 │
         │                                             │
         │  ┌──────────────────────────────────────┐  │
         │  │  Authentication Middleware            │  │
         │  │  (verify_domain_id)                  │  │
         │  └──────────────────────────────────────┘  │
         │                    │                        │
         │                    ▼                        │
         │  ┌──────────────────────────────────────┐  │
         │  │     API Endpoints                     │  │
         │  │                                       │  │
         │  │  • POST /register-domain             │  │
         │  │  • POST /session                     │  │
         │  │  • POST /ask (with Memori)           │  │
         │  │  • POST /scrape (manual only)        │  │
         │  │  • POST /knowledge/upload/*          │  │
         │  │  • GET  /knowledge/supported-types   │  │
         │  └──────────────────────────────────────┘  │
         │                    │                        │
         │                    ▼                        │
         │  ┌──────────────────────────────────────┐  │
         │  │   Core Components                     │  │
         │  │                                       │  │
         │  │  • DigitalOceanClient                │  │
         │  │    (digitalocean_client.py)          │  │
         │  │  • MemoriIntegration                 │  │
         │  │    (memori_integration.py)           │  │
         │  │  • KnowledgeUploader                 │  │
         │  │    (knowledge_upload.py)             │  │
         │  └──────────────────────────────────────┘  │
         └────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ DigitalOcean│  │   Memori    │  │ PostgreSQL  │
     │  Gradient   │  │  (Direct    │  │  Database   │
     │     AI      │  │   Database  │  │  • Sessions │
     │  (Agents &  │  │Integration) │  │  • Domains  │
     │     KBs)    │  │  + Gradient │  │  • Agents   │
     │             │  │     AI)     │  │  • Memori   │
     └─────────────┘  └─────────────┘  └─────────────┘
```

## Memori Integration

### Key Changes from Previous Version

**Before (API-based):**
- Used Memori API endpoint for conversation storage
- Required HTTP calls to external Memori service
- Per-domain API key management

**After (Direct Integration):**
- Direct database integration via SQLAlchemy
- DigitalOcean Gradient AI agent wrapped by Memori
- No API keys required for Memori
- Automatic conversation tracking and fact extraction
- Zero-latency context recall with semantic search
- No additional API keys needed (uses Gradient AI credentials)
- Background augmentation for fact extraction

### How Memori Works

```python
# Initialize once at startup
memori = Memori(conn=SessionLocal)
memori.config.storage.build()  # Create schema

# For each conversation - create client and register with Memori
client = OpenAI(base_url=agent_endpoint, api_key=agent_access_key)
memori.set_context(user_id, session_id, domain_id)
memori.openai.register(client)
response = client.chat.completions.create(...)  # Automatic memory capture
```

**Automatic Features:**
1. **Context Injection**: Relevant facts from past conversations are automatically added to system prompts
2. **Fact Extraction**: Background thread extracts facts without blocking responses
3. **Semantic Search**: Vector embeddings enable finding relevant context
4. **Session Grouping**: Conversations are grouped by session for context continuity
5. **Entity Attribution**: Memories tied to specific users (entities) and agents (processes)

## API Endpoints

### Domain Management

#### POST /register-domain
Registers a new domain and creates its agent infrastructure.

**Flow**:
1. Validate API key and domain_name
2. Generate unique API key for domain
3. Create DigitalOcean agent (empty KB list)
4. Start background polling for deployment
5. Create fresh access key via POST /agents/{uuid}/api_keys
6. Extract access key from api_key_info.secret_key
7. After deployment: Attach knowledge bases
8. Return immediately (non-blocking)

**Response**: Domain ID and API key

**Key Changes**:
- Uses domain_name for website_key generation
- Creates access key after agent creation
- Background polling handles deployment wait
- Memori uses direct database integration (no API keys)

### Session Management

#### POST /session
Creates a user session for a domain.

**Headers**: X-Domain-ID

**Flow**:
1. Lookup domain in registered_domains
2. Extract domain_name (not website_url)
3. Create session record
4. Memori v3 automatically tracks session context
5. Return session_id

**Key Changes**:
- NO automatic /scrape call (widget updated)
- Session tied to domain_name
- Memori handles session grouping automatically

### Chat Interaction

#### POST /ask
Processes user questions with AI agent and Memori memory.

**Headers**: X-Domain-ID

**Flow (Updated for Memori)**:
1. Lookup domain → domain_info {domain_name}
2. Generate website_key from domain_name
3. Retrieve agent from cache/DB
4. Verify agent has valid access_key (create if missing)
5. **[NEW]** Initialize Memori context: `memori.set_context(user_id, session_id, domain_id)`
6. **[NEW]** Create OpenAI client with agent credentials: `OpenAI(base_url=agent_url, api_key=access_key)`
7. **[NEW]** Register client with Memori: `memori.openai.register(client)`
8. **[NEW]** Call via Memori: Automatic context recall + fact extraction
9. **[NEW]** Fallback to direct agent call if Memori fails
10. Save conversation to database
11. Return response

**Key Changes**:
- Direct Memori integration replaces API calls
- Uses DigitalOcean Gradient AI agent (no OpenAI API key needed)
- Automatic context injection (no manual enhancement needed)
- Background fact extraction (zero latency impact)
- Fallback mechanism for reliability

**Memori Flow Details:**
```
User Question → Create OpenAI client with agent credentials
             → Memori.set_context(user, session, domain)
             → Memori.openai.register(client)
             → OpenAI call (wrapped by Memori)
             → Memori recalls relevant facts
             → Facts added to system prompt automatically
             → Gradient AI agent generates response
             → Memori stores conversation
             → Background: Extract facts for future recall
```

### Knowledge Management

#### POST /knowledge/upload/file
Upload files to domain's knowledge base.

**Headers**: X-Domain-ID

**Process**: Same as before (see Data Flow Example)

#### POST /scrape
Manual website scraping (admin only).

**Key Changes**:
- NO longer called automatically by widget
- Admin/manual trigger only

## Data Flow Example: PDF Upload

```
1. Client Request
   POST /knowledge/upload/file
   ├─ Authorization: Bearer API_KEY
   ├─ website_url: "https://example.com"
   ├─ file: product_manual.pdf (2.5 MB)
   └─ chunk_size: 1000

2. Authentication
   verify_domain_id(api_key)
   ├─ Query registered_domains table
   ├─ Validate API key
   └─ ✓ Authorized

3. File Processing
   KnowledgeUploader.upload_from_bytes()
   ├─ Save to temp file: /tmp/abc123.pdf
   ├─ Detect file type: .pdf
   └─ Select reader: PDFReader

4. Reader Configuration
   PDFReader(
     chunk=True,
     chunk_size=1000,
     chunking_strategy=RecursiveChunking(
       chunk_size=1000,
       overlap=100
     )
   )

5. Content Extraction
   PDF (50 pages) → Raw Text
   ├─ Page 1: "Introduction to Product..."
   ├─ Page 2: "Installation Steps..."
   ├─ ...
   └─ Page 50: "Troubleshooting..."

6. Chunking
   Raw Text → 75 chunks
   ├─ Chunk 1 (1000 chars): "Introduction to Product..."
   ├─ Chunk 2 (1000 chars): "...features. Installation..."
   ├─ ...
   └─ Chunk 75 (834 chars): "...contact support."

7. Embedding Generation
   For each chunk → OpenAI API
   ├─ Chunk 1 → [0.123, -0.456, ..., 0.789] (1536 dims)
   ├─ Chunk 2 → [0.234, -0.567, ..., 0.890]
   └─ ...

8. Storage
   Insert into PostgreSQL
   ├─ Table: website_knowledge_example_com
   ├─ 75 rows inserted
   └─ Each row: (id, embedding, content, metadata)

9. Response
   {
     "success": true,
     "message": "Successfully uploaded product_manual.pdf",
     "details": {
       "filename": "product_manual.pdf",
       "file_type": ".pdf",
       "file_size": 2621440,
       "chunk_size": 1000,
       "chunking_strategy": "recursive"
     }
   }

10. Cleanup
    ├─ Delete temp file: /tmp/abc123.pdf
    └─ Return success response
```

## Query Flow: Using Uploaded Knowledge

```
1. User Question (via Widget)
   "How do I install the product?"

2. Domain & Session Lookup
   ├─ X-Domain-ID header → registered_domains table
   ├─ Extract domain_info: {domain_name, api_key}
   ├─ Generate website_key from domain_name (not session URL)
   ├─ session_id → user_sessions table
   └─ Consistent agent lookup: agents[website_key]

3. Agent Retrieval
   ├─ Check memory cache first
   ├─ Fallback to database if not cached
   ├─ Verify agent has valid access_key (32 chars)
   └─ If missing, create new key via POST /agents/{uuid}/api_keys

4. DigitalOcean Agent API Call
   GET https://{agent_url}/api/v1/chat/completions
   Headers:
   ├─ Authorization: Bearer {agent_access_key}
   └─ Content-Type: application/json
   Body:
   └─ {"messages": [{"role": "user", "content": "..."}]}

5. Agent Processing (DigitalOcean)
   ├─ Knowledge Base Retrieval (automatic)
   ├─ Vector search in attached KBs
   ├─ Top-K relevant chunks retrieved
   └─ Context injected into prompt

6. Response Generation
   "To install the product:
    1. Download the installer from...
    2. Run the installer and...
    3. Configure your settings..."

7. Memori Integration (Domain-Specific)
   MemoriClient.chat()
   ├─ Endpoint: https://memori-api-89r6e.ondigitalocean.app/v1/chat
   ├─ API Key: domain_info.api_key (per-domain)
   ├─ Context: {assistant_id, session_id, user_id}
   ├─ Save user question
   ├─ Save AI response
   └─ Store in isolated domain memory

8. Response to User
   {
     "answer": "To install the product...",
     "sources": ["product_manual.pdf"],
     "session_id": "uuid-here"
   }

9. Widget Display
   ├─ NO automatic /scrape call (removed)
   ├─ Display AI response
   └─ Maintain chat history in UI
```

## Database Schema

```sql
-- Agent and Knowledge Base Persistence

-- Agents table (stores DigitalOcean Gradient AI agents)
CREATE TABLE agents (
    website_key TEXT PRIMARY KEY,          -- Hash of domain_name from registered_domains
    agent_uuid UUID NOT NULL,
    agent_url TEXT NOT NULL,
    agent_access_key TEXT,                 -- Freshly created API key (32 chars)
    website_url TEXT NOT NULL,             -- Normalized as https://{domain_name}
    knowledge_base_uuids TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON agents(website_url);
CREATE INDEX ON agents(agent_uuid);

-- Knowledge bases table (stores DigitalOcean knowledge bases)
CREATE TABLE knowledge_bases (
    website_key TEXT PRIMARY KEY,
    kb_uuid UUID NOT NULL,
    website_url TEXT NOT NULL,
    kb_name TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON knowledge_bases(website_url);
CREATE INDEX ON knowledge_bases(kb_uuid);

-- Domain Registration (stores per-domain configuration)
CREATE TABLE registered_domains (
    id UUID PRIMARY KEY,
    domain_name TEXT UNIQUE NOT NULL,      -- Base domain (no www, no protocol)
    api_key TEXT UNIQUE NOT NULL,          -- API key for this domain's endpoints
    created_at TIMESTAMP DEFAULT NOW()
);

-- User Sessions
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    website_url TEXT,                      -- Derived from domain_name
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP,
    status TEXT DEFAULT 'active'
);

-- Conversation History
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES user_sessions(session_id),
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Key Architecture Decisions

### 1. Domain-Based Agent Lookup
**Problem**: URL variations (www vs non-www, different subdomains) caused duplicate agents.

**Solution**:
- Store normalized `domain_name` in `registered_domains` table
- Generate `website_key` from registered `domain_name`, not client URL
- Normalize `website_url` as `https://{domain_name}`

**Impact**: Single agent per registered domain, regardless of URL variations.

### 2. Access Key Management
**Problem**: Keys from `agent.api_keys` array were invalid, causing 401 errors.

**Discovery Process**:
```bash
# Testing old key from agent response
curl .../chat/completions -H "Authorization: Bearer OLD_KEY"
→ {"detail": "Invalid access token"}  # 401 error

# Creating fresh key via API
curl -X POST .../agents/{uuid}/api_keys -d '{"name": "key-{website_key}"}'
→ {"api_key_info": {"secret_key": "NEW_KEY", ...}}

# Testing new key
curl .../chat/completions -H "Authorization: Bearer NEW_KEY"
→ Success! AI response returned
```

**Solution**:
- **Always create fresh keys**: POST to `/agents/{uuid}/api_keys`
- **Extract from correct field**: `api_key_info.secret_key` (not `api_key.api_key`)
- **Applied in 3 locations**:
  1. `create_agent()` - Initial agent creation
  2. `check_and_update_agent_url()` - On-demand URL updates
  3. `poll_agent_deployment_background()` - Background deployment completion

**Impact**: All agents now have valid access keys, 401 errors eliminated.

### 3. Memori Client Architecture
**Problem**: Memori API calls scattered throughout main.py.

**Solution**:
- Created dedicated `memori_integration.py` module
- `MemoriIntegration` class with direct database integration
- Uses DigitalOcean Gradient AI agent credentials
- Each domain has isolated memory context via user_id

**Benefits**:
- Clean separation of concerns
- Easier testing and maintenance
- Per-domain memory isolation
- Reusable across different endpoints

### 4. Widget Auto-Scraping Removal
**Problem**: Widget automatically called `/scrape` endpoint on every session, causing unnecessary load.

**Solution**:
- Removed `scrapeWebsite()` function from `widget.js`
- Removed automatic scrape call during initialization
- Scraping now manual via admin endpoints only

**Impact**: Reduced backend load, faster widget initialization.

### 5. Knowledge Base Attachment Timing
**Problem**: Attaching KBs during agent creation caused 404 errors (agent not ready).

**Solution**:
- Create agent with empty KB list
- Poll until deployment completes (STATUS_RUNNING)
- Attach KBs after agent is fully deployed
- Background task handles polling without blocking

**Impact**: Eliminates 404 errors, reliable KB attachment.

## Component Responsibilities

### Agent Persistence Manager
- Save agents to database with domain-based website_key
- Load agents from database on startup
- Cache agents in memory for fast access
- Automatic synchronization with DigitalOcean
- **Domain-based lookup**: Uses registered domain_name to prevent duplicates
- **Access key management**: Creates fresh API keys via POST /agents/{uuid}/api_keys

### Knowledge Base Manager
- Save knowledge bases to database
- Load KBs from database on startup
- Cache KBs in memory for fast access
- Track KB-to-website mappings
- **Post-deployment attachment**: Attaches KBs after agent deployment completes

### KnowledgeUploader
- File type detection
- Reader selection
- Temporary file management
- Error handling
- Response formatting

### DigitalOcean Gradient AI Client (digitalocean_client.py)
- Agent creation and management
- Knowledge base creation
- Web crawler data sources
- File upload with presigned URLs
- Indexing job management
- **Access key creation**: POST /agents/{uuid}/api_keys
- **Response parsing**: Extracts api_key_info.secret_key (not agent.api_keys)

### Memori Integration (memori_integration.py)
- **Dedicated module**: Separated from main.py for clean architecture
- **MemoriIntegration class**: Direct database integration with Gradient AI
- **Per-agent credentials**: Uses domain-specific agent_url and agent_access_key
- **Methods**:
  - `chat()`: Send messages with automatic context recall
  - Creates OpenAI-compatible client per request
  - Wraps Gradient AI agent with Memori memory layer
- **Database**: Automatic schema creation via SQLAlchemy
- **Memory**: Persistent conversation history per user_id

### Vector Database (DigitalOcean)
- Embedding storage
- Similarity search
- Metadata filtering
- Index management

### DigitalOcean Agent
- Knowledge retrieval
- Context integration
- Chat completions API
- Response generation
- **Access token authentication**: Uses freshly created API keys
- **Authorization**: Bearer token in request headers

### Memori (External Service)
- Conversation memory per domain
- Context persistence across sessions
- User preferences
- Session continuity
- **Isolation**: Each registered domain has separate memory context

## Performance Metrics

### Database Persistence
```
Operation            | Time      | Description
---------------------|-----------|---------------------------
Load Agents (startup)| 50-200ms  | Load all agents from DB
Load KBs (startup)   | 50-200ms  | Load all KBs from DB
Save Agent          | 10-50ms   | Save new agent to DB
Save KB             | 10-50ms   | Save new KB to DB
Agent Lookup (mem)  | < 1ms     | Check memory cache (domain-based)
Agent Lookup (DB)   | 5-20ms    | Fallback to database
Access Key Creation | 100-300ms | POST /agents/{uuid}/api_keys
Domain Lookup       | 5-15ms    | Query registered_domains table
```

### Agent Creation & Deployment
```
Operation                  | Time         | Description
---------------------------|--------------|---------------------------
Create Agent (API call)    | 500-1500ms   | POST to DigitalOcean
Agent Deployment (polling) | 60-180 sec   | Wait for STATUS_RUNNING
Background Polling         | Non-blocking | Async task, no user wait
KB Attachment (post-deploy)| 200-500ms    | After agent is ready
Total Setup Time (blocking)| 1-2 sec      | User gets immediate response
Total Setup Time (complete)| 60-180 sec   | Background completion
```

### Upload Performance
```
File Type    | Size    | Processing Time | Chunks
-------------|---------|-----------------|--------
PDF (10pg)   | 500KB   | 2-5 sec        | 15-20
PDF (100pg)  | 5MB     | 10-30 sec      | 150-200
TXT (small)  | 50KB    | < 1 sec        | 5-10
MD (medium)  | 200KB   | 1-2 sec        | 20-30
JSON         | 100KB   | 1-2 sec        | 10-15
CSV          | 500KB   | 2-3 sec        | 50-100
URL Scrape   | N/A     | 30-300 sec     | 50-500
```

### Query Performance
```
Operation              | Time
-----------------------|------------
Domain Lookup          | 5-15 ms
Agent Retrieval (cache)| < 1 ms
Agent Retrieval (DB)   | 5-20 ms
DO Agent API Call      | 500-2000 ms
Memori API Call        | 200-500 ms
Total Query Time       | 1-3 sec
```

### Resource Usage
```
Component           | Memory | CPU    | Storage
--------------------|--------|--------|----------
Agents (cached)     | 1KB ea | -      | 500B/agent
KBs (cached)        | 100B ea| -      | 200B/kb
File Upload         | 50MB   | 20%    | -
Session Management  | 10MB   | 5%     | 1KB/session
Memori Client       | 2MB    | < 1%   | -
Background Tasks    | 5MB    | 2%     | -
```

## Error Handling Flow

```
Request → Validation → Processing → Storage → Response
    │          │           │           │
    ├─ 400 ───┤           │           │
    │          ├─ 500 ────┤           │
    │          │           ├─ 500 ────┤
    │          │           │           │
    └──────────┴───────────┴───────────┴─── Error Response
```

## Security Layers

```
┌──────────────────────────────────┐
│   1. HTTPS/TLS Encryption        │
└──────────────────────────────────┘
                │
┌──────────────────────────────────┐
│   2. Bearer Token Authentication │
└──────────────────────────────────┘
                │
┌──────────────────────────────────┐
│   3. Domain Verification         │
└──────────────────────────────────┘
                │
┌──────────────────────────────────┐
│   4. File Type Validation        │
└──────────────────────────────────┘
                │
┌──────────────────────────────────┐
│   5. Size Limit Checks           │
└──────────────────────────────────┘
                │
┌──────────────────────────────────┐
│   6. SQL Injection Prevention    │
└──────────────────────────────────┘
```

## Troubleshooting & Known Issues

### Issue 1: Invalid Access Token (401 Errors) ✅ FIXED

**Symptoms**:
- Error: "Agent API error: 401 - Invalid access token"
- Occurs when calling DigitalOcean agent chat completions
- Key present in database but doesn't work

**Root Cause**:
- Agent response contains `api_keys` array with old/invalid keys
- Extracting keys from `agent.api_keys[0].api_key` produces invalid tokens

**Investigation**:
```bash
# Test stored key
curl .../chat/completions -H "Authorization: Bearer fss2ko7rbNqoNguFZayv..."
→ {"detail": "Invalid access token"}  # FAILED

# Create new key
curl -X POST .../agents/{uuid}/api_keys -d '{"name": "test"}'
→ {"api_key_info": {"secret_key": "im9YSesRZT12pVnQ...", ...}}

# Test new key
curl .../chat/completions -H "Authorization: Bearer im9YSesRZT12pVnQ..."
→ AI response returned  # SUCCESS!
```

**Solution**:
1. Always create fresh keys: `POST /agents/{uuid}/api_keys`
2. Extract from correct field: `api_key_info.secret_key`
3. Applied in 3 locations: create_agent, check_and_update, background polling

**Files Modified**:
- `digitalocean_client.py` line 430: Return `api_key_info` not `api_key`
- `main.py` lines 714-731, 828-842, 914-931: Create fresh keys

### Issue 2: Duplicate Agents Per Domain ✅ FIXED

**Symptoms**:
- Multiple agents created for same domain
- Different website_keys for www.example.com vs example.com
- Knowledge bases not shared across sessions

**Root Cause**:
- Using session `website_url` (from client) to generate website_key
- URL variations (www prefix, different subdomains) create different keys

**Solution**:
- Use registered `domain_name` from `registered_domains` table
- Normalize as `https://{domain_name}` before generating website_key
- Single agent per registered domain

**Files Modified**:
- `main.py` lines 1138-1163: Use domain_info.get("domain_name")

### Issue 3: Knowledge Base 404 Errors ✅ FIXED

**Symptoms**:
- Error attaching KBs to agent: 404 Not Found
- Occurs immediately after agent creation

**Root Cause**:
- Agents not fully deployed when trying to attach KBs
- Agent exists but URL not ready yet

**Solution**:
- Create agent with empty KB list
- Poll until `deployment.status == "STATUS_RUNNING"`
- Attach KBs after deployment completes
- Background task handles polling (non-blocking)

**Files Modified**:
- `main.py`: Background polling with KB attachment after deployment

### Issue 4: Memori Integration ✅ FIXED

**Symptoms**:
- All domains shared same conversation memory
- Users could see other domains' conversations

**Root Cause**:
- Used external API with global key
- No per-domain isolation

**Solution**:
- Direct database integration via SQLAlchemy
- Per-domain agent credentials (agent_url, agent_access_key)
- Memori creates isolated tables per user_id

**Files Modified**:
- `memori_integration.py`: New direct integration module
- `main.py`: Pass agent credentials to Memori

### Issue 5: Widget Auto-Scraping ✅ FIXED

**Symptoms**:
- High backend load from /scrape calls
- Slow widget initialization
- Unnecessary duplicate scraping

**Root Cause**:
- Widget automatically calling /scrape on every session
- Even when knowledge already exists

**Solution**:
- Removed `scrapeWebsite()` function from widget.js
- Removed automatic scrape call
- Scraping now manual/admin only

**Files Modified**:
- `static/widget.js` lines 535-547: Removed scrape logic

## Best Practices

### 1. Access Key Management
- ✅ Always create fresh keys via POST /api_keys
- ✅ Extract from api_key_info.secret_key
- ❌ Never use agent.api_keys array (contains invalid keys)
- ✅ Store keys in database with agent record
- ✅ Verify key length = 32 characters

### 2. Domain Management
- ✅ Use registered domain_name for website_key generation
- ✅ Normalize URLs as https://{domain_name}
- ❌ Don't use client-provided URLs for agent lookup
- ✅ Single agent per registered domain
- ✅ Per-domain memory isolation via Memori's database integration

### 3. Agent Deployment
- ✅ Create agent with empty KB list first
- ✅ Poll until STATUS_RUNNING before attaching KBs
- ✅ Use background tasks for non-blocking deployment
- ✅ Return immediately to user, complete in background
- ❌ Don't attach KBs during agent creation (causes 404)

### 4. Knowledge Base Operations
- ✅ Attach KBs after agent deployment completes
- ✅ Use presigned URLs for large file uploads
- ✅ Monitor indexing job status
- ✅ Cache KB UUIDs in database
- ✅ Reuse existing KBs when possible

### 5. Session & Chat
- ✅ Widget creates session without auto-scraping
- ✅ Use X-Domain-ID header for authentication
- ✅ Domain-specific Memori integration per request
- ✅ Cache agents in memory for fast lookup
- ✅ Fallback to database if not cached
