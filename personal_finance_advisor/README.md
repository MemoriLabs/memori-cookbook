# Personal Finance Advisor with Transaction Memory

An AI-powered **Personal Finance Advisor** built with **React** + **FastAPI** that uses **Memori v3** for long-term memory and **OpenAI** with **LangGraph** for personalized financial advice and goal-setting.

## Features

- 💰 **Transaction Tracking** - Log and categorize all your transactions with automatic pattern recognition
- 📊 **Spending Analysis** - Track spending patterns, identify trends, and get insights on your financial habits
- 🎯 **Financial Goals** - Set and track financial goals with AI-powered recommendations
- 💳 **Budget Management** - Create budgets and monitor adherence with real-time alerts
- 🔄 **Recurring Expenses** - Automatically identify and track recurring expenses
- 📈 **Financial Health Assessments** - Get comprehensive financial health assessments using LangGraph
- 🧠 **Long-Term Memory** - Every transaction is remembered using Memori's long-term storage
- 💡 **Personalized Advice** - Receive specific, actionable financial advice based on your unique patterns

---

## Project Structure

```
personal_finance_advisor/
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
├── core.py              # AI logic (financial assessments, goal-setting, budget analysis)
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
cd personal_finance_advisor

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
   - **Name**: `personal-finance-advisor-api`
   - **Root Directory**: (leave empty or set to repo root)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -e .`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. Add environment variables (optional, for default keys):
   ```
   OPENAI_API_KEY=your_key_here
   MEMORI_API_KEY=your_key_here
   ```

5. Deploy! Note your backend URL (e.g., `https://personal-finance-advisor-api.onrender.com`)

#### Deploy Frontend to Vercel

1. Update the API base URL in `frontend/src/components/Dashboard.tsx`:
   ```typescript
   const API_BASE = "https://personal-finance-advisor-api.onrender.com";
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

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | Yes (user provides in UI) |
| `MEMORI_API_KEY` | Memori API key for long-term memory | Yes (user provides in UI) |
| `FINANCE_SQLITE_PATH` | Custom SQLite database path | No (default: `./memori_finance.sqlite`) |
| `FINANCE_MODEL` | OpenAI model to use | No (default: `gpt-4o-mini`) |

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
- **Planning**: LangGraph (via Agno) for financial health assessments and goal-setting

---

## How It Works

1. **Transaction Logging**: Users log transactions which are stored in Memori for long-term memory
2. **Pattern Recognition**: The system automatically identifies spending patterns and recurring expenses
3. **Budget Tracking**: Users create budgets and the system monitors adherence
4. **Financial Health Assessments**: LangGraph conducts comprehensive assessments to review financial status
5. **Goal Setting**: LangGraph helps set and track financial goals with personalized recommendations
6. **Long-Term Memory**: All data is stored in Memori for context-aware financial advice over time

---

Made with ❤️ using [Memori](https://memorilabs.ai) Memory Fabric
