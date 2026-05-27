# Quick Reference Guide — Customer Support AI API

## Base URL
```
http://localhost:8000  # Development
https://your-api.com   # Production
```

## Authentication
All protected endpoints require the domain ID issued at registration:
```
X-Domain-ID: YOUR_DOMAIN_ID
```

---

## Agent & Knowledge Base Persistence

Agents and knowledge bases are automatically persisted to the database and survive restarts.

**Startup log:**
```
✓ Database connection successful
DEBUG: Loaded X agents from database
DEBUG: Loaded Y knowledge bases from database
```

---

## 📊 Health Check

**`GET /health`**

```bash
curl http://localhost:8000/health
```

```json
{
    "status": "healthy",
    "database": "connected",
    "digitalocean": "ok",
    "timestamp": "2025-10-28T10:30:00",
    "active_sessions": 5,
    "active_agents": 3,
    "knowledge_bases": 5
}
```

---

## 🌐 Register Domain

**`POST /register-domain`**

```bash
curl -X POST http://localhost:8000/register-domain \
  -H "Content-Type: application/json" \
  -d '{"domain_name": "example.com"}'
```

```json
{
    "message": "Domain registered successfully",
    "domain_id": "uuid-here",
    "agent_created": true,
    "agent_uuid": "agent-uuid-here",
    "agent_deployment_status": "STATUS_WAITING_FOR_DEPLOYMENT",
    "deployment_message": "Agent created successfully. Deployment will complete in 1-2 minutes."
}
```

> Copy the `domain_id` — you need it as the `X-Domain-ID` header for all subsequent requests.

---

## 🔐 Session Management

**`POST /session`**

**Headers:** `X-Domain-ID` (not required for session creation, but needed for `/ask`)

```bash
curl -X POST http://localhost:8000/session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "website_url": "https://example.com"}'
```

```json
{
    "session_id": "uuid-here",
    "user_id": "user123",
    "created_at": "2025-10-28T10:30:00",
    "website_url": "https://example.com"
}
```

---

## 💬 Ask Question

**`POST /ask`**

**Headers:** `X-Domain-ID` (required)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -d '{
    "question": "How do I reset my password?",
    "session_id": "uuid-here",
    "user_id": "user123"
  }'
```

```json
{
    "answer": "To reset your password...",
    "sources": [],
    "session_id": "uuid-here"
}
```

---

## 📄 Upload File

**`POST /knowledge/upload/file`** — `multipart/form-data`

**Headers:** `X-Domain-ID` (required)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| file | file | ✅ | — | `.pdf`, `.txt`, `.md`, `.json`, `.csv` |
| chunk_size | integer | ❌ | 1000 | Size of text chunks |
| use_semantic | boolean | ❌ | false | Semantic chunking |
| custom_name | string | ❌ | filename | Custom document name |

```bash
curl -X POST http://localhost:8000/knowledge/upload/file \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -F "file=@document.pdf"
```

```json
{
    "success": true,
    "message": "Successfully uploaded document.pdf to knowledge base",
    "details": {
        "filename": "document.pdf",
        "file_size": 524288,
        "knowledge_base_uuid": "kb-uuid-here",
        "data_source_uuid": "ds-uuid-here",
        "indexing_job_uuid": "job-uuid-here"
    }
}
```

---

## 📝 Upload Text

**`POST /knowledge/upload/text`** — `application/json`

**Headers:** `X-Domain-ID` (required)

```bash
curl -X POST http://localhost:8000/knowledge/upload/text \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -H "Content-Type: application/json" \
  -d '{"text_content": "FAQ content here", "document_name": "FAQ"}'
```

---

## 🌐 Upload from URL

**`POST /knowledge/upload/url`** — `application/json`

**Headers:** `X-Domain-ID` (required)

```bash
curl -X POST http://localhost:8000/knowledge/upload/url \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -H "Content-Type: application/json" \
  -d '{"url_to_scrape": "https://docs.example.com", "max_depth": 2, "max_links": 20}'
```

---

## 📚 List Agents

**`GET /agents`**

```bash
curl http://localhost:8000/agents
```

```json
{
    "agents": [
        {
            "website_key": "abc123",
            "agent_uuid": "agent-uuid",
            "website_url": "https://example.com",
            "agent_url": "https://api.digitalocean.com/...",
            "has_access_key": true,
            "created_at": "2025-10-28T10:00:00",
            "knowledge_base_uuids": ["kb-uuid-1"]
        }
    ],
    "total": 1,
    "note": "One agent per website, shared across all sessions. Memori provides user/session context."
}
```

---

## 📚 Supported File Types

**`GET /knowledge/supported-types`**

```bash
curl http://localhost:8000/knowledge/supported-types
```

```json
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

---

## 💬 Conversation History

**`GET /conversations/{session_id}`**

```bash
curl http://localhost:8000/conversations/SESSION_ID
```

---

## 🗄️ Database Monitoring

```sql
-- All registered domains
SELECT id, domain_name, created_at FROM registered_domains ORDER BY created_at DESC;

-- All agents
SELECT website_key, agent_uuid, website_url, LENGTH(agent_access_key) as key_len
FROM agents ORDER BY created_at DESC;

-- All knowledge bases
SELECT website_key, kb_uuid, website_url, kb_name FROM knowledge_bases ORDER BY created_at DESC;

-- Resource counts
SELECT
    (SELECT COUNT(*) FROM registered_domains) as total_domains,
    (SELECT COUNT(*) FROM agents) as total_agents,
    (SELECT COUNT(*) FROM knowledge_bases) as total_kbs,
    (SELECT COUNT(*) FROM user_sessions WHERE status = 'active') as active_sessions;
```

---

## Error Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad request (missing required header or invalid parameters) |
| 401 | Unauthorized (unknown domain_id) |
| 404 | Not found |
| 500 | Server error |
| 503 | Agent still deploying — retry in 1-2 minutes |

---

## Python Client Example

```python
import requests

class CustomerSupportClient:
    def __init__(self, api_url, domain_id):
        self.api_url = api_url
        self.headers = {"X-Domain-ID": domain_id}

    def register_domain(self, domain_name):
        response = requests.post(
            f"{self.api_url}/register-domain",
            json={"domain_name": domain_name}
        )
        return response.json()

    def create_session(self, user_id):
        response = requests.post(
            f"{self.api_url}/session",
            json={"user_id": user_id}
        )
        return response.json()

    def ask(self, question, session_id, user_id):
        response = requests.post(
            f"{self.api_url}/ask",
            headers=self.headers,
            json={"question": question, "session_id": session_id, "user_id": user_id}
        )
        return response.json()

    def upload_file(self, file_path):
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.api_url}/knowledge/upload/file",
                headers=self.headers,
                files={"file": f}
            )
        return response.json()

    def upload_text(self, text_content, document_name):
        response = requests.post(
            f"{self.api_url}/knowledge/upload/text",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"text_content": text_content, "document_name": document_name}
        )
        return response.json()

# Usage
client = CustomerSupportClient("http://localhost:8000", "YOUR_DOMAIN_ID")
session = client.create_session("user123")
answer = client.ask("How do I reset my password?", session["session_id"], "user123")
print(answer["answer"])
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 503 on `/ask` | Agent still deploying | Wait 1-2 min and retry |
| 401 on any endpoint | Wrong or missing `X-Domain-ID` | Register domain first, use returned `domain_id` |
| 400 on `/register-domain` | Invalid domain format | Use bare hostname: `example.com`, not `https://example.com` |
| Widget not loading | Static files 404 | Run uvicorn from parent dir: `uvicorn customer_support_agent_memory.main:app` |

---

## Quick Tips

- **Chunk size:** 500–800 for short docs, 1000–1500 for medium, 1500–2000 for large
- **Semantic chunking:** Better for technical docs and research papers; standard is fine for FAQs and tables
- **One agent per domain:** Shared across all users — Memori handles per-user memory
- **Agent deployment takes 1-2 min:** The widget shows a friendly message during this window
