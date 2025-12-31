# Technical Interview Prep Assistant

An AI-powered **Technical Interview Prep Assistant** built with **React** + **FastAPI** that uses **Memori v3** for long-term memory and **OpenAI** for coaching.

## Features

- 🧑‍💻 **Profile & Goals** - Set up your candidate profile with target role, experience level, and goals
- 🧠 **Practice Sessions** - Get AI-generated personalized coding problems with hints and evaluations
- 🎯 **Mock Interviews** - Simulate real phone screens and onsite interviews with timed sessions
- 📊 **Visual Analytics** - Track progress with charts showing patterns, difficulty breakdown, and trends
- 🔄 **Spaced Repetition** - Review problems at optimal intervals with SM-2 algorithm
- 🏢 **Company Prep** - Focus on patterns commonly asked at Google, Meta, Amazon, etc.
- 📅 **AI Study Plans** - Get personalized weekly study plans based on your weak patterns
- 💬 **Ask Coach** - Chat with a Memori-backed assistant about your progress

---

## Project Structure

```
technical_interview_prep_agent/
├── backend/
│   ├── main.py          # FastAPI backend
│   └── database.py      # SQLAlchemy models & helpers
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.ts
├── core.py              # AI logic (problem generation, hints, evaluation)
├── memory_utils.py      # Memori integration
├── pyproject.toml       # Python dependencies
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API Key
- Memori API Key (get one at [memorilabs.ai](https://memorilabs.ai))

### Backend Setup

```bash
cd technical_interview_prep_agent

# Install Python dependencies
uv sync
# or: pip install -e .

# Run the FastAPI backend
uv run uvicorn backend.main:app --reload --port 8000
# or: uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

The frontend runs on `http://localhost:5173` and the backend on `http://localhost:8000`.

---

## Deployment

### Option 1: Deploy Frontend (Vercel) + Backend (Render) - Recommended

This is the recommended approach for production.

#### Deploy Backend to Render

1. Create a new **Web Service** on [Render](https://render.com)

2. Connect your GitHub repository

3. Configure the service:
   - **Name**: `interview-prep-api`
   - **Root Directory**: (leave empty or set to repo root)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -e .`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. Add environment variables (optional, for default keys):
   ```
   OPENAI_API_KEY=your_key_here
   MEMORI_API_KEY=your_key_here
   ```

5. Deploy! Note your backend URL (e.g., `https://interview-prep-api.onrender.com`)

#### Deploy Frontend to Vercel

1. Update the API base URL in `frontend/src/components/Dashboard.tsx`:
   ```typescript
   const API_BASE = "https://interview-prep-api.onrender.com";
   ```

2. Create a new project on [Vercel](https://vercel.com)

3. Connect your GitHub repository

4. Configure the project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Deploy!

---

### Option 2: Deploy Both to Render

You can also deploy both frontend and backend to Render.

#### Backend (same as above)

#### Frontend as Static Site

1. Create a new **Static Site** on Render

2. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

3. Add a rewrite rule for SPA routing:
   - Source: `/*`
   - Destination: `/index.html`

---

### Option 3: Deploy as Monorepo on Render

Create a `render.yaml` at your repo root:

```yaml
services:
  # Backend API
  - type: web
    name: interview-prep-api
    runtime: python
    buildCommand: pip install -e .
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"

  # Frontend Static Site
  - type: web
    name: interview-prep-frontend
    runtime: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
```

Then use **Render Blueprints** to deploy both services together.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | Yes (user provides in UI) |
| `MEMORI_API_KEY` | Memori API key for long-term memory | Yes (user provides in UI) |
| `INTERVIEW_SQLITE_PATH` | Custom SQLite database path | No (default: `./memori_interview.sqlite`) |
| `INTERVIEW_MODEL` | OpenAI model to use | No (default: `gpt-4o-mini`) |

**Note**: Users provide their own API keys via the dashboard UI. No default keys are required on the server.

---

## Production Considerations

1. **CORS**: Update the CORS origins in `backend/main.py` to match your frontend domain:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-frontend-domain.vercel.app"],
       ...
   )
   ```

2. **Database**: For production, consider using a persistent database:
   - Render: Use a Render PostgreSQL database
   - Or: Mount a persistent disk for SQLite

3. **API Keys**: Users bring their own keys, so no server-side key management is needed.

---

## Tech Stack

- **Frontend**: React, TypeScript, Vite
- **Backend**: FastAPI, Python
- **Database**: SQLite (via SQLAlchemy)
- **AI**: OpenAI GPT-4o-mini
- **Memory**: Memori v3

---

Made with ❤️ using [Memori](https://memorilabs.ai) Memory Fabric
