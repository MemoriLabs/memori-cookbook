# Customer Support Agent — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                          │
├─────────────────────────────────────────────────────────────────────┤
│  widget.js (embedded)  │  demo.html  │  knowledge_upload_demo.html  │
└────────────────────────┴─────────────┴──────────────────────────────┘
                                │
                    HTTP with X-Domain-ID header
                                │
                                ▼
         ┌────────────────────────────────────────────┐
         │              FastAPI Application            │
         │                                             │
         │  POST /register-domain                      │
         │  POST /session                              │
         │  POST /ask          ← Memori-wrapped        │
         │  POST /knowledge/upload/{file,text,url}     │
         │  GET  /conversations/{session_id}           │
         │  GET  /agents  /knowledge-bases  /health    │
         └────────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
     ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
     │ DigitalOcean│   │    Memori    │   │  PostgreSQL  │
     │  Gradient   │   │  (direct DB  │   │  • Sessions  │
     │  AI Agents  │   │ integration) │   │  • Domains   │
     │  + KBs      │   │              │   │  • Agents    │
     └─────────────┘   └──────────────┘   │  • Memori    │
                                           └──────────────┘
```

## Authentication

All protected endpoints use an `X-Domain-ID` header containing the UUID returned by `POST /register-domain`. There is no Bearer token or API key system.

```
X-Domain-ID: <domain_uuid>
```

The server looks up this UUID in the `registered_domains` table to identify the domain on every request.

## Component Responsibilities

### `main.py` — FastAPI Application

- Domain registration → creates DigitalOcean agent in background
- Session management → persists to PostgreSQL
- `/ask` → routes through Memori for automatic memory integration
- Knowledge upload endpoints → delegate to DigitalOcean presigned URL flow
- In-memory caches for agents and knowledge bases with DB fallback

### `digitalocean_client.py` — DigitalOcean Gradient AI Client

Wraps the DigitalOcean Gen AI REST API:
- `create_knowledge_base()` — with initial web crawler datasource
- `create_agent()` — binds model + KB + system prompt
- `create_agent_access_key()` — always creates a fresh key (old keys from the agent response are invalid)
- `attach_knowledge_base()` — only after `deployment.status == STATUS_RUNNING`
- `add_web_crawler_data_source()`, `add_file_data_source()`, `start_indexing_job()`
- `create_presigned_url_for_file()` — for direct S3-compatible uploads

### `memori_integration.py` — Memori Layer

Wraps the DigitalOcean Gradient AI agent with Memori's persistent memory:

```python
# One-time setup
mem = Memori(conn=SessionLocal)

# Per-request — set who is talking and which agent
mem.attribution(entity_id=user_id, process_id=f"support-agent-{domain_id}")

# Register the OpenAI-compatible client once per endpoint
client = OpenAI(base_url=agent_url, api_key=agent_access_key)
mem.openai.register(client)

# Call like normal — Memori injects recalled facts + stores new ones
response = client.chat.completions.create(model="n/a", messages=[...])
```

**What Memori does automatically:**
1. Recalls relevant facts from this user's past conversations (semantic search)
2. Injects those facts into the system prompt before the LLM sees the message
3. Extracts new facts from the response in the background
4. Stores everything in PostgreSQL under the user's entity

**Attribution scoping** ensures memories from domain A never appear in domain B:
- `entity_id` = user ID (who is speaking)
- `process_id` = `"support-agent-{domain_uuid}"` (which domain's agent)

## Key Design Decisions

### 1. One Agent Per Domain, Memori Per User
DigitalOcean agents are expensive to create and shared. Memori provides the per-user personalisation layer on top, so you get both scale and memory without creating one agent per user.

### 2. Non-Blocking Agent Deployment
Agent creation returns immediately. A background `asyncio` task polls `deployment.status` until `STATUS_RUNNING` (1–2 min), then attaches knowledge bases. The `/ask` endpoint returns a 503 with a friendly message during this window.

### 3. Access Key Creation
Keys bundled in the agent creation response are stale and cause 401s. The code always calls `POST /agents/{uuid}/api_keys` to create a fresh key after deployment.

### 4. Domain-Based website_key
`website_key = md5(f"https://{domain_name}")[:16]`

Generated from the registered `domain_name`, not from the client-supplied URL. This prevents duplicate agents when the same site is accessed as `www.example.com` vs `example.com`.

### 5. KB Attachment After Deployment
Attaching knowledge bases before `STATUS_RUNNING` returns 404. The background polling task handles attachment once the agent is live.

## Data Flow: `/ask` Endpoint

```
POST /ask
  X-Domain-ID: <uuid>
  {"question": "...", "session_id": "...", "user_id": "..."}

  1. Lookup domain_id in registered_domains → get domain_name
  2. Generate website_key from domain_name
  3. Get agent from memory cache / DB / create new
  4. If agent_url missing → poll DigitalOcean for deployment status → 503 if not ready
  5. Run in thread pool (Memori is sync):
       mem.attribution(entity_id=user_id, process_id="support-agent-{domain_id}")
       client = OpenAI(base_url=agent_url, api_key=agent_access_key)
       mem.openai.register(client)  # registers once per endpoint
       response = client.chat.completions.create(...)
       # ↑ Memori automatically:
       #   - recalls relevant past facts → injects into context
       #   - stores conversation → extracts facts in background
  6. Save conversation to conversation_history table
  7. Return {"answer": "...", "sources": [], "session_id": "..."}
```

## Data Flow: Domain Registration

```
POST /register-domain {"domain_name": "example.com"}

  1. Validate domain format
  2. INSERT into registered_domains → get UUID
  3. create_agent(website_url="https://example.com", wait_for_deployment=False)
     a. create_knowledge_base() with web crawler datasource for domain
     b. create_agent() — empty KB list (attaching before STATUS_RUNNING causes 404)
     c. create_agent_access_key() — fresh key
     d. Save agent to DB with deployment_status
  4. Start background task: poll_agent_deployment_background()
     a. wait_for_agent_deployment() — polls every 5s up to 180s
     b. On STATUS_RUNNING: attach_knowledge_base(), create new access key, save to DB
  5. Return immediately with domain_id + agent_uuid + deployment_status
```

## Data Flow: Knowledge Upload

```
POST /knowledge/upload/file   (multipart/form-data, X-Domain-ID)

  1. Lookup domain → website_url
  2. Get or create knowledge_base for this domain
  3. create_presigned_url_for_file() → get S3 presigned URL
  4. PUT file bytes to presigned URL (direct to DigitalOcean Spaces)
  5. add_file_data_source() — register the uploaded object with the KB
  6. start_indexing_job() — trigger embedding + vector indexing
  7. Return {success, message, details: {kb_uuid, data_source_uuid, job_uuid}}
```

## Database Schema

```sql
registered_domains (id UUID PK, domain_name TEXT UNIQUE, created_at)
user_sessions      (session_id UUID PK, user_id, website_url, created_at, last_activity, status)
agents             (website_key TEXT PK, agent_uuid, agent_url, agent_access_key,
                    website_url, knowledge_base_uuids TEXT[], deployment_status, created_at, updated_at)
knowledge_bases    (website_key TEXT PK, kb_uuid, website_url, kb_name,
                    database_id, created_at, updated_at)
conversation_history (id UUID PK, session_id FK, user_id, role, content, created_at)
digitalocean_config  (config_key TEXT PK, config_value, created_at, updated_at)

-- Memori tables (auto-created by Memori on first run):
memori_entity, memori_process, memori_session, memori_conversation,
memori_conversation_message, memori_entity_fact, memori_knowledge_graph, ...
```

## Performance Characteristics

| Operation | Typical Time |
|-----------|-------------|
| Domain registration (returns to caller) | ~1.5s |
| Agent deployment (background) | 60–180s |
| KB attachment (after deployment) | ~300ms |
| `/ask` (cold, no cached client) | 1–3s |
| `/ask` (warm, cached client) | 0.8–2s |
| File upload (PDF, 1MB) | 3–8s |
| URL scrape + index | 30–300s |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 503 on `/ask` | Agent deploying | Wait 1–2 min; check logs for "Background polling completed" |
| 401 on `/ask` | Wrong/missing X-Domain-ID | Use domain_id UUID from `/register-domain` response |
| `Not Found` on `/static/*` | Wrong working directory | Run `uvicorn` from parent of `customer_support_agent_memory/` |
| Duplicate agents | Using client URL instead of domain_name | Fixed by design — website_key derived from registered domain_name |
| Memori not recalling | domain_id lookup was returning "unknown" | Fixed — uses `domain_info["id"]` not `domain_info["domain_id"]` |
