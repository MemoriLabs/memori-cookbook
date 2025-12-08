# Quick Reference Guide - Customer Support AI API

## Base URL
```
http://localhost:8000  # Development
https://your-api.com   # Production
```

## Authentication
Most endpoints require domain verification via header:
```
X-Domain-Id: YOUR_DOMAIN_ID
```

---

## 🤖 Agent & Knowledge Base Persistence

**Note:** Agents and knowledge bases are automatically persisted to the database. They survive application restarts.

### On Application Startup
```
✓ Database connection successful
DEBUG: Loaded X agents from database
DEBUG: Loaded Y knowledge bases from database
```

### Agent Lifecycle
1. Check memory cache (fast)
2. If not found, check database
3. If not found, create new agent via DigitalOcean API
4. Save to both memory and database

### Knowledge Base Lifecycle
1. Check memory cache (fast)
2. If not found, check database
3. If not found, create new KB via DigitalOcean API
4. Save to both memory and database

---

## 📊 Health Check

**Endpoint:** `GET /health`

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
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

## 🔐 Session Management

**Endpoint:** `POST /session`

**Body:**
```json
{
    "user_id": "user123",
    "website_url": "https://example.com"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/session" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","website_url":"https://example.com"}'
```

**Response:**
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

**Endpoint:** `POST /ask`

**Headers:**
- `X-Domain-Id`: YOUR_DOMAIN_ID (optional)

**Body:**
```json
{
    "question": "How do I reset my password?",
    "session_id": "uuid-here",
    "user_id": "user123",
    "website_context": "https://example.com/login"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -H "X-Domain-Id: YOUR_DOMAIN_ID" \
  -d '{
    "question": "How do I reset my password?",
    "session_id": "uuid-here",
    "user_id": "user123"
  }'
```

**Response:**
```json
{
    "answer": "To reset your password...",
    "sources": [],
    "session_id": "uuid-here"
}
```

---

---

## 📄 Upload File (DigitalOcean)

**Endpoint:** `POST /knowledge/upload/file`

**Content-Type:** `multipart/form-data`

**Headers:**
- `X-Domain-ID`: YOUR_DOMAIN_ID

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| file | file | ✅ Yes | - | File to upload (.pdf, .txt, .md, .json, .csv) |
| chunk_size | integer | ❌ No | 1000 | Size of text chunks |
| use_semantic | boolean | ❌ No | false | Use semantic chunking |
| custom_name | string | ❌ No | filename | Custom document name |

**Note:** Uses DigitalOcean's presigned URL upload + indexing jobs

**Example:**
```bash
curl -X POST "http://localhost:8000/knowledge/upload/file" \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -F "file=@document.pdf"
```

**Success Response:**
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

## 📝 Upload Text (DigitalOcean)

**Endpoint:** `POST /knowledge/upload/text`

**Content-Type:** `application/json`

**Headers:**
- `X-Domain-ID`: YOUR_DOMAIN_ID

**Body:**
```json
{
    "text_content": "Your text content here",
    "document_name": "My Document",
    "chunk_size": 1000,
    "use_semantic": false
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/knowledge/upload/text" \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -H "Content-Type: application/json" \
  -d '{"text_content":"FAQ content","document_name":"FAQ"}'
```

---

## 🌐 Upload from URL (DigitalOcean Web Crawler)

**Endpoint:** `POST /knowledge/upload/url`

**Content-Type:** `application/json`

**Headers:**
- `X-Domain-ID`: YOUR_DOMAIN_ID

**Body:**
```json
{
    "url_to_scrape": "https://docs.example.com",
    "max_depth": 2,
    "max_links": 20,
    "chunk_size": 1000
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/knowledge/upload/url" \
  -H "X-Domain-ID: YOUR_DOMAIN_ID" \
  -H "Content-Type: application/json" \
  -d '{"url_to_scrape":"https://docs.example.com"}'
```

---

## 🕷️ Scrape Website (DigitalOcean Web Crawler)

**Endpoint:** `POST /scrape-website`

**Body:**
```json
{
    "website_url": "https://example.com",
    "depth": 2,
    "max_pages": 20
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/scrape-website" \
  -H "Content-Type: application/json" \
  -d '{
    "website_url": "https://example.com",
    "depth": 2,
    "max_pages": 20
  }'
```

**Response:**
```json
{
    "success": true,
    "pages_scraped": 15,
    "message": "Successfully indexed https://example.com",
    "website_url": "https://example.com"
}
```

---

---

## 📚 List Agents

**Endpoint:** `GET /agents`

**Example:**
```bash
curl http://localhost:8000/agents
```

**Response:**
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
    "total": 1
}
```

---

## 📚 Get Supported File Types

**Endpoint:** `GET /knowledge/supported-types`

**Example:**
```bash
curl -X GET "http://localhost:8000/knowledge/supported-types"
```

**Response:**
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
    "additional_sources": ["url", "text"],
    "registered_domain": "example.com",
    "website_url": "https://example.com"
}
```

---

## 🗄️ Database Persistence

### Automatic Persistence
All agents and knowledge bases are automatically saved to PostgreSQL:
- ✅ Survives application restarts
- ✅ Fast memory cache for lookups
- ✅ Database fallback for recovery
- ✅ No manual intervention needed

### Monitoring Queries

**Check stored agents:**
```sql
SELECT website_key, agent_uuid, website_url, created_at
FROM agents
ORDER BY created_at DESC;
```

**Check stored knowledge bases:**
```sql
SELECT website_key, kb_uuid, website_url, kb_name
FROM knowledge_bases
ORDER BY created_at DESC;
```

**Count resources:**
```sql
SELECT
    (SELECT COUNT(*) FROM agents) as total_agents,
    (SELECT COUNT(*) FROM knowledge_bases) as total_kbs,
    (SELECT COUNT(*) FROM user_sessions WHERE status = 'active') as active_sessions;
```

### Migration

**For existing installations:**
```bash
psql -h localhost -U do_user -d customer_support -f migrate_db.sql
```

See `DATABASE_PERSISTENCE.md` for full documentation.

---

## Response Format

### Success Response
```json
{
    "success": true,
    "message": "Successfully uploaded document.pdf",
    "details": {
        "filename": "document.pdf",
        "file_type": ".pdf",
        "file_size": 524288,
        "chunk_size": 1000,
        "chunking_strategy": "recursive"
    }
}
```

### Error Response
```json
{
    "success": false,
    "message": "Error message here"
}
```

---

## Quick Tips

### ✅ Chunk Size Selection
- **Small docs (< 10 pages):** 500-800
- **Medium docs (10-50 pages):** 1000-1500
- **Large docs (> 50 pages):** 1500-2000

### ✅ When to Use Semantic Chunking
- ✓ Technical documentation
- ✓ Research papers
- ✓ Legal documents
- ✗ FAQs (use standard)
- ✗ Lists (use standard)
- ✗ Tables (use standard)

### ✅ Supported File Types
| Extension | Description | Reader |
|-----------|-------------|--------|
| .pdf | PDF documents | PDFReader |
| .txt | Plain text | TextReader |
| .md | Markdown | MarkdownReader |
| .json | JSON data | JSONReader |
| .csv | CSV data | CSVReader |

---

## Error Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not found |
| 500 | Server error |
| 504 | Timeout (scraping took too long) |

---

## Testing

### Web Demo
Visit: `http://localhost:8000/knowledge-upload-demo`

### Health Check
```bash
curl http://localhost:8000/health
```

---

## Common Issues

### Issue: "Unsupported file type"
**Solution:** Check file extension. Only .pdf, .txt, .md, .json, .csv are supported.

### Issue: "Unauthorized"
**Solution:** Check your domain ID is correct and included in X-Domain-ID header.

### Issue: Upload timeout
**Solution:** For URLs, reduce max_depth or max_links. For files, try smaller chunk_size.

### Issue: Poor search results
**Solution:** Try semantic chunking or adjust chunk_size.

---

## Python Client Example

```python
import requests

class KnowledgeClient:
    def __init__(self, api_url, domain_id):
        self.api_url = api_url
        self.headers = {"X-Domain-ID": domain_id}

    def upload_file(self, file_path, chunk_size=1000):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'chunk_size': chunk_size
            }
            response = requests.post(
                f"{self.api_url}/knowledge/upload/file",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()

    def upload_text(self, text_content, document_name):
        response = requests.post(
            f"{self.api_url}/knowledge/upload/text",
            headers=self.headers,
            json={
                'text_content': text_content,
                'document_name': document_name
            }
        )
        return response.json()

# Usage
client = KnowledgeClient("http://localhost:8000", "YOUR_DOMAIN_ID")
result = client.upload_file("document.pdf")
print(result)
```

---

## JavaScript Client Example

```javascript
class KnowledgeClient {
    constructor(apiUrl, domainId) {
        this.apiUrl = apiUrl;
        this.domainId = domainId;
    }

    async uploadFile(file, chunkSize = 1000) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chunk_size', chunkSize);

        const response = await fetch(`${this.apiUrl}/knowledge/upload/file`, {
            method: 'POST',
            headers: {
                'X-Domain-ID': this.domainId
            },
            body: formData
        });
        return await response.json();
    }

    async uploadText(textContent, documentName) {
        const response = await fetch(`${this.apiUrl}/knowledge/upload/text`, {
            method: 'POST',
            headers: {
                'X-Domain-ID': this.domainId,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text_content: textContent,
                document_name: documentName
            })
        });
        return await response.json();
    }
}

// Usage
const client = new KnowledgeClient('http://localhost:8000', 'YOUR_DOMAIN_ID');
const result = await client.uploadText(
    'FAQ content',
    'Customer FAQ'
);
console.log(result);
```

---

## Need Help?

- 📖 **Full Documentation:** See `KNOWLEDGE_UPLOAD_EXAMPLES.md`
- 🎮 **Interactive Demo:** Visit `/knowledge-upload-demo`
- 📝 **API Docs:** Visit `/docs` (Swagger UI)
- 🐛 **Issues:** Check logs or contact support
