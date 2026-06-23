# Persistent Memory Dev Agent

A multi-agent developer workflow powered by [Memori](https://memorilabs.ai). Four specialized agents — Coder, Reviewer, Tester, Docs — collaborate on any dev task and **share memory scoped to your current git branch**. Switch branches and the swarm automatically loads the right context. No manual copy-paste. No lost decisions. No token blowup.

---

## Why this exists

Enterprise dev teams hit three walls with LLM-assisted coding:

| Problem | What happens | What Memori does |
|---|---|---|
| **Context loss** | Every new session starts cold — re-explain the PR, the constraints, the decisions | Agents remember across sessions automatically |
| **Token blowup** | Full codebase + history dumped into every prompt as the project grows | Intelligent recall injects only what's relevant (~150 tokens vs. 10,000+) |
| **Agent silos** | Coder, Reviewer, and Tester work off different context and contradict each other | All agents share the same branch-scoped memory mesh |

---

## Quickstart

```bash
git clone https://github.com/MemoriLabs/memori-cookbook
cd memori-cookbook/persistent_memory_dev_agent

cp .env.example .env
# Fill in MEMORI_API_KEY and your LLM provider key (GOOGLE_API_KEY, OPENAI_API_KEY, etc.)

uv sync
python run.py swarm "Add JWT refresh token support"
```

That's it. The swarm reads your current git branch, loads any prior memory for it, runs all four agents in sequence, and saves context for next time.

---

## How it works

### Branch-scoped memory

Every piece of context — decisions, review findings, test coverage gaps — is stored under a key derived from your repo name and current branch:

```
entity_id = "my-repo/feat/auth-refactor"
process_id = "memori-mesh"
```

**Switch branches → get that branch's memory.** The swarm never confuses work from `feat/auth` with `feat/payments`. This is handled in three lines:

```python
from memori import Memori
from openai import OpenAI

client = OpenAI(api_key="...")
mem = Memori().llm.register(client)             # wrap the client
mem.attribution(entity_id="repo/branch", process_id="memori-mesh")  # scope to branch
# use client normally — Memori intercepts, recalls, and stores automatically
```

### Agent pipeline

Agents run sequentially. Each agent's output becomes the next agent's input, so the Reviewer sees exactly what the Coder proposed, and the Tester knows what the Reviewer flagged.

```
Task → [Coder] → [Reviewer] → [Tester] → [Docs] → Results saved to Memori
         ↑____________ shared branch memory ____________↑
```

---

## Commands

```bash
# Run the full swarm
python run.py swarm "Add rate limiting to the API"

# Run a subset of agents
python run.py swarm "Review the DB migration" --agents reviewer,tester

# Run in a different repo
python run.py swarm "Refactor auth" --repo ~/code/my-project

# See the current branch memory scope and git context
python run.py branch-status

# Token savings demo — shows before/after numbers without calling the API
python run.py token-demo
```

---

## Example prompts

Copy any of these directly into the task field or CLI:

```bash
python run.py swarm "Add rate limiting to a REST API endpoint"
python run.py swarm "Refactor synchronous database calls to async"
python run.py swarm "Implement JWT refresh token rotation"
python run.py swarm "Add OpenTelemetry tracing to a FastAPI service"
python run.py swarm "Design a retry and exponential backoff strategy for an external API client"
python run.py swarm "Extract a monolithic auth module into a standalone service"
python run.py swarm "Add database migration safety checks before deployment"
python run.py swarm "Implement an idempotency key pattern for a payments endpoint"
```

---

## Token savings demo

Shows the difference between naive full-context prompting and Memori-powered recall across a realistic 4-session auth refactor:

```
python run.py token-demo
```

```
  #   Task                                              Before   After   Saved
  ─────────────────────────────────────────────────────────────────────────────
  1   What security issues exist in our auth module?    3,847      21    99%
  2   What's our migration plan for the JWT changes?    4,521     171    96%
  3   Reviewer flagged concurrent refresh — what did…   5,198     175    97%
  4   Implement the refresh token rotation endpoint…    5,874     178    97%

  BEFORE (full context):   19,440 tokens   $0.0029
  AFTER  (Memori):            545 tokens   $0.0001
  Reduction:                     97% fewer tokens   $0.0028 saved

  At scale — 50 devs × 20 sessions/day: $2.80/day saved
```

Numbers use tiktoken (gpt-4o-mini encoding). Session 1 has no prior memories to recall so Memori injects nothing; sessions 2+ receive ~150 tokens of recalled context. Pricing shown is illustrative (gpt-4o-mini at $0.15/1M tokens) — run `python run.py token-demo` to see exact counts for your setup.

For accurate token counts, install tiktoken:

```bash
uv pip install tiktoken
```

---

## Multi-provider support

Works with Google Gemini, OpenAI, Anthropic, and AWS Bedrock. Set `LLM_PROVIDER` and the matching key in `.env`:

```bash
# Gemini (default)
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIza...
LLM_MODEL=gemini-2.5-flash

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-6

# AWS Bedrock
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

---

## Project structure

```
persistent_memory_dev_agent/
├── agents/
│   ├── base.py          # Memori registration + attribution, shared by all agents
│   ├── coder.py         # Implementation planning agent
│   ├── reviewer.py      # Code review agent
│   ├── tester.py        # Test generation agent
│   └── docs.py          # Documentation agent
├── core/
│   ├── config.py        # Pydantic settings (provider keys, model selection)
│   └── git_context.py   # Branch detection, repo name, changed files
├── demos/
│   └── token_savings.py # Before/after token comparison (runs without API keys)
├── tests/
│   ├── conftest.py
│   └── test_agents.py
├── app.py               # Streamlit UI — run with: uv run python -m streamlit run app.py
├── swarm.py             # Orchestrator — chains agents, prints rich output
├── run.py               # CLI entry point (click)
├── pyproject.toml
└── .env.example
```

---

## Streamlit UI

A browser-based interface for the agent swarm — type your task, pick your agents, and watch results stream in. API keys and provider can be changed from the sidebar without touching `.env`.

```bash
uv run python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). The sidebar shows your current git branch and recent commits so you always know which memory scope is active. After each run, a token savings widget shows how many tokens Memori saved compared to naive full-context prompting.

---

## Running tests

```bash
uv sync --extra dev
uv run pytest
```

To also run the live Memori integration test (requires `MEMORI_API_KEY`):

```bash
uv run pytest -m integration
```

---

## The three lines that make this work

```python
from memori import Memori
from openai import OpenAI

client = OpenAI(api_key="...")
mem = Memori().llm.register(client)      # 1. wrap
mem.attribution(entity_id="repo/branch", process_id="memori-mesh")  # 2. scope
response = client.chat.completions.create(...)  # 3. use — memory is automatic
```

Memori intercepts the call, retrieves relevant memories for `repo/branch`, augments the prompt, sends it to the LLM, and stores new memories from the response. Your code doesn't change.

---

## Ideas for extending this

- **Slack bot** — surface swarm outputs to the team channel on every PR
- **CI integration** — run the Reviewer and Tester agents on every push, post findings as PR comments
- **Cross-branch diffing** — compare memory from `feat/A` and `feat/B` before merging to catch conflicts early
- **Agent specialization** — add a Security agent, an Architecture agent, or a Performance agent
