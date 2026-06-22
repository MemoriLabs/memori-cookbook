"""
Persistent Memory Dev Agent — Streamlit UI
Multi-agent dev swarm with git-branch-scoped memory via Memori.
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

from agents.coder import CoderAgent
from agents.docs import DocsAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from core.config import get_settings
from core.git_context import (
    get_changed_files,
    get_context_id,
    get_current_branch,
    get_recent_commits,
)

st.set_page_config(page_title="Persistent Memory Dev Agent", layout="wide", page_icon="🧠")

# ── Brand colors (memorilabs.ai) ──────────────────────────────────────────────
# Primary: #712fff  Blue: #0080ff  Orange: #F47725  Green: #006b48  Dark: #0B0C0D

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; }

/* ─ Page bg ─ */
.main { background: #f9fafb !important; }
.main .block-container {
    padding: 2.5rem 2.5rem 4rem !important;
    max-width: 860px !important;
}

/* ─ Sidebar — light ─ */
section[data-testid="stSidebar"] > div:first-child {
    background: #ffffff !important;
    border-right: 1px solid #ede9fe !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #5b20e0 !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    margin: 1.1rem 0 0.4rem !important;
}
section[data-testid="stSidebar"] label {
    color: #292929 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] .stCaption p {
    color: #656565 !important;
    font-size: 0.78rem !important;
}
section[data-testid="stSidebar"] input {
    background: #faf9ff !important;
    border: 1px solid #ede9fe !important;
    color: #292929 !important;
    border-radius: 7px !important;
    font-size: 0.82rem !important;
    font-family: 'Roboto', sans-serif !important;
}
section[data-testid="stSidebar"] input:focus {
    border-color: #712fff !important;
    box-shadow: 0 0 0 2px rgba(113,47,255,0.15) !important;
    outline: none !important;
}
section[data-testid="stSidebar"] input::placeholder { color: #989898 !important; }
section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
    background: #faf9ff !important;
    border: 1px solid #ede9fe !important;
    border-radius: 7px !important;
    color: #292929 !important;
}
section[data-testid="stSidebar"] .stCheckbox span {
    color: #292929 !important;
    font-size: 0.84rem !important;
}
section[data-testid="stSidebar"] [data-testid="stCode"] {
    background: #faf9ff !important;
    border: 1px solid #ede9fe !important;
    border-radius: 7px !important;
}
section[data-testid="stSidebar"] [data-testid="stCode"] code {
    color: #712fff !important;
    font-size: 0.73rem !important;
}
section[data-testid="stSidebar"] hr { border-color: #f3f0ff !important; margin: 0.7rem 0 !important; }
section[data-testid="stSidebar"] .stButton button {
    background: #ffffff !important;
    color: #712fff !important;
    border: 1.5px solid #712fff !important;
    border-radius: 7px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: #f3f0ff !important;
    color: #5b20e0 !important;
    border-color: #5b20e0 !important;
}
section[data-testid="stSidebar"] .stAlert { border-radius: 7px !important; }

/* ─ Main textarea ─ */
.stTextArea textarea {
    font-family: 'Roboto', sans-serif !important;
    border-radius: 10px !important;
    border: 1.5px solid #e9e0ff !important;
    font-size: 0.95rem !important;
    line-height: 1.65 !important;
    color: #0B0C0D !important;
    background: #ffffff !important;
    box-shadow: 0 1px 4px rgba(113,47,255,0.06) !important;
    padding: 14px 16px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextArea textarea:focus {
    border-color: #712fff !important;
    box-shadow: 0 0 0 3px rgba(113,47,255,0.12) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: #989898 !important; }
.stTextArea label { display: none !important; }

/* ─ Run button ─ */
.stButton button[kind="primary"] {
    background: #712fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.55rem 1.6rem !important;
    box-shadow: 0 2px 10px rgba(113,47,255,0.3) !important;
    transition: box-shadow 0.15s, transform 0.1s !important;
    color: #fff !important;
}
.stButton button[kind="primary"]:hover:not(:disabled) {
    background: #5b20e0 !important;
    box-shadow: 0 4px 18px rgba(113,47,255,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton button[kind="primary"]:disabled {
    background: #e9e0ff !important;
    box-shadow: none !important;
    color: #6d28d9 !important;
}

/* ─ Result/status panels ─ */
[data-testid="stStatus"] {
    border-radius: 10px !important;
    border: 1.5px solid #ede9fe !important;
    background: #ffffff !important;
    box-shadow: 0 2px 8px rgba(113,47,255,0.06) !important;
    margin-bottom: 10px !important;
}

/* ─ Expander ─ */
[data-testid="stExpander"] {
    border: 1.5px solid #ede9fe !important;
    border-radius: 10px !important;
    background: #fff !important;
}

/* ─ Download button ─ */
.stDownloadButton button {
    border-radius: 7px !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    border-color: #ede9fe !important;
    color: #712fff !important;
}

/* ─ Typography ─ */
hr { border-color: #f3f0ff !important; margin: 1.5rem 0 !important; }
code { font-size: 0.82rem !important; border-radius: 4px !important; }
pre { border-radius: 8px !important; }
p { font-size: 0.95rem !important; line-height: 1.7 !important; color: #292929 !important; }

/* ─ Example prompt chips ─ */
div[data-testid="column"] .stButton button:not([kind="primary"]) {
    background: #faf9ff !important;
    border: 1.5px solid #ede9fe !important;
    border-radius: 100px !important;
    color: #5b20e0 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 1rem !important;
    box-shadow: none !important;
    text-align: left !important;
    transition: all 0.15s !important;
}
div[data-testid="column"] .stButton button:not([kind="primary"]):hover {
    background: #f3f0ff !important;
    border-color: #712fff !important;
    color: #712fff !important;
    box-shadow: 0 2px 8px rgba(113,47,255,0.12) !important;
    transform: translateY(-1px) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
# Agent colors from Memori brand palette
PIPELINE: list[tuple[str, type, str, str]] = [
    ("Coder",    CoderAgent,    "⌨",  "#0080ff"),   # brand blue
    ("Reviewer", ReviewerAgent, "🔍", "#F47725"),   # brand orange
    ("Tester",   TesterAgent,   "✅", "#006b48"),   # brand green
    ("Docs",     DocsAgent,     "📄", "#712fff"),   # brand purple
]

PROVIDERS = ["Gemini", "OpenAI", "Anthropic", "AWS Bedrock"]

DB_BACKENDS = [
    "Memori Cloud",
    "CockroachDB",
    "MariaDB",
    "MongoDB",
    "MySQL",
    "OceanBase",
    "Oracle",
    "PostgreSQL",
    "SQLite",
    "TiDB",
]

DB_BACKEND_ENV = {
    "Memori Cloud": "cloud",
    "SQLite":       "sqlite",
    "PostgreSQL":   "postgresql",
    "MySQL":        "mysql",
    "MariaDB":      "mariadb",
    "MongoDB":      "mongodb",
    "CockroachDB":  "cockroachdb",
    "TiDB":         "tidb",
    "OceanBase":    "oceanbase",
    "Oracle":       "oracle",
}

DEFAULT_MODELS = {
    "Gemini":      "gemini-2.5-flash",
    "OpenAI":      "gpt-4o-mini",
    "Anthropic":   "claude-sonnet-4-6",
    "AWS Bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
}

PROVIDER_ENV = {
    "Gemini": "gemini", "OpenAI": "openai",
    "Anthropic": "anthropic", "AWS Bedrock": "bedrock",
}

EXAMPLE_PROMPTS = [
    "Keep users logged in safely with refresh token rotation",
    "Make database calls non-blocking for better performance",
    "Prevent API abuse with per-user rate limits",
    "Add tracing so we can debug slow or failing requests",
    "Make the payment endpoint safe to retry without double-charging",
    "Catch risky database changes before they hit production",
]

AGENT_DESCRIPTIONS = {
    "Coder":    "Plans the implementation",
    "Reviewer": "Catches bugs & edge cases",
    "Tester":   "Writes comprehensive tests",
    "Docs":     "Writes developer docs",
}


def apply_keys(
    provider: str, memori: str, key1: str, key2: str, model_name: str, region: str,
    db_backend: str = "cloud", db_conn_str: str = "", db_path: str = "memori.db",
) -> None:
    os.environ["LLM_PROVIDER"] = PROVIDER_ENV[provider]
    if memori:      os.environ["MEMORI_API_KEY"] = memori
    if provider == "Gemini"    and key1: os.environ["GOOGLE_API_KEY"]        = key1
    if provider == "OpenAI"    and key1: os.environ["OPENAI_API_KEY"]        = key1
    if provider == "Anthropic" and key1: os.environ["ANTHROPIC_API_KEY"]     = key1
    if provider == "AWS Bedrock":
        if key1: os.environ["AWS_ACCESS_KEY_ID"]     = key1
        if key2: os.environ["AWS_SECRET_ACCESS_KEY"] = key2
        os.environ["AWS_REGION"] = region
    if model_name: os.environ["LLM_MODEL"] = model_name
    os.environ["DB_BACKEND"] = db_backend
    if db_backend == "sqlite":
        os.environ["DB_PATH"] = db_path
    elif db_backend != "cloud" and db_conn_str:
        os.environ["DB_CONNECTION_STRING"] = db_conn_str
    get_settings.cache_clear()


def agent_header_html(name: str, emoji: str, color: str, thinking: bool = False) -> str:
    badge = (
        f'<span style="font-size:0.7rem;color:{color};background:{color}18;'
        f'padding:2px 9px;border-radius:100px;font-weight:500;margin-left:6px;">thinking…</span>'
        if thinking else ""
    )
    return (
        f'<div style="display:flex;align-items:center;padding:13px 18px 12px;'
        f'background:#fdfcff;border-bottom:1px solid #f3f0ff;'
        f'border-radius:10px 10px 0 0;border-top:3px solid {color};">'
        f'<span style="font-size:1rem;line-height:1;margin-right:8px;">{emoji}</span>'
        f'<span style="font-weight:600;font-size:0.86rem;color:#0B0C0D;">{name}</span>'
        f'{badge}</div>'
        f'<div style="padding:16px 18px 8px;">'
    )


# ── Session state — token savings ─────────────────────────────────────────────
if "tokens_actual" not in st.session_state:
    st.session_state.tokens_actual = 0
    st.session_state.tokens_naive = 0
    st.session_state.accumulated_output_chars = 0
if "task_area" not in st.session_state:
    st.session_state.task_area = ""

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 2px;">
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:3px;">
            <span style="font-size:1.3rem;">🧠</span>
            <span style="font-weight:700;font-size:1rem;color:#0B0C0D;letter-spacing:-0.01em;">Persistent Memory Dev Agent</span>
        </div>
        <p style="margin:0;font-size:0.72rem;color:#656565;">Multi-agent dev swarm</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("### API Keys")
    memori_key = st.text_input("Memori API Key", value=os.getenv("MEMORI_API_KEY", ""), type="password")
    provider_label = st.selectbox("LLM Provider", PROVIDERS)

    llm_key = llm_key2 = ""
    region_val = "us-east-1"

    if provider_label == "Gemini":
        llm_key = st.text_input("Google API Key", value=os.getenv("GOOGLE_API_KEY", ""), type="password")
    elif provider_label == "OpenAI":
        llm_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    elif provider_label == "Anthropic":
        llm_key = st.text_input("Anthropic API Key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")
    else:
        llm_key  = st.text_input("AWS Access Key ID",     value=os.getenv("AWS_ACCESS_KEY_ID",     ""), type="password")
        llm_key2 = st.text_input("AWS Secret Access Key", value=os.getenv("AWS_SECRET_ACCESS_KEY", ""), type="password")
        region_val = st.text_input("Region", value=os.getenv("AWS_REGION", "us-east-1"))

    model = st.text_input("Model", value=os.getenv("LLM_MODEL", DEFAULT_MODELS[provider_label]))

    st.divider()
    st.markdown("### Memory storage")
    current_backend_env = os.getenv("DB_BACKEND", "cloud")
    current_backend_label = next(
        (k for k, v in DB_BACKEND_ENV.items() if v == current_backend_env),
        "Memori Cloud",
    )
    db_label = st.selectbox("Database", DB_BACKENDS, index=DB_BACKENDS.index(current_backend_label))

    db_conn_str_val = ""
    db_path_val = "memori.db"

    if db_label == "SQLite":
        db_path_val = st.text_input("File path", value=os.getenv("DB_PATH", "memori.db"))
    elif db_label != "Memori Cloud":
        db_conn_str_val = st.text_input(
            "Connection string",
            value=os.getenv("DB_CONNECTION_STRING", ""),
            type="password",
            placeholder={
                "PostgreSQL":  "postgresql+psycopg://user:pass@host/db",
                "MySQL":       "mysql+pymysql://user:pass@host/db",
                "MariaDB":     "mysql+pymysql://user:pass@host/db",
                "MongoDB":     "mongodb://localhost:27017/memori",
                "CockroachDB": "cockroachdb+psycopg2://user:pass@host:26257/db",
                "TiDB":        "mysql+pymysql://user:pass@host:4000/db",
                "OceanBase":   "mysql+pyobvector://user:pass@host:2881/db",
                "Oracle":      "oracle+oracledb://user:pass@host:1521/service",
            }.get(db_label, ""),
        )

    if st.button("Save settings", type="primary", use_container_width=True):
        apply_keys(
            provider_label, memori_key, llm_key, llm_key2, model, region_val,
            db_backend=DB_BACKEND_ENV[db_label],
            db_conn_str=db_conn_str_val,
            db_path=db_path_val,
        )
        st.success("Saved")

    st.divider()
    st.markdown("### Agents")
    selected_agents: list[str] = []
    for name, _, emoji, color in PIPELINE:
        if st.checkbox(name, value=True, key=f"chk_{name}"):
            selected_agents.append(name)

    st.divider()
    st.markdown("### Current workspace")
    try:
        branch  = get_current_branch()
        commits = get_recent_commits(n=3)
        changed = get_changed_files()

        # Human-readable branch name: "feat/multi-provider" → "Multi provider"
        readable_branch = branch.split("/")[-1].replace("-", " ").replace("_", " ").capitalize()
        st.markdown(
            f'<div style="font-size:0.8rem;font-weight:600;color:#712fff;'
            f'background:#f3f0ff;border-radius:6px;padding:5px 10px;margin-bottom:8px;">'
            f'📁 {readable_branch}</div>',
            unsafe_allow_html=True,
        )

        if commits:
            st.markdown(
                '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#5b20e0;margin:6px 0 4px;">Recent changes</p>',
                unsafe_allow_html=True,
            )
            for c in commits:
                # Strip the git hash prefix (first 7 chars + space)
                msg = c[8:].strip() if len(c) > 8 else c
                # Remove conventional commit prefixes like "fix:", "feat:", "style:"
                for prefix in ("fix: ", "feat: ", "style: ", "chore: ", "docs: ", "refactor: ", "test: "):
                    if msg.lower().startswith(prefix):
                        msg = msg[len(prefix):]
                        break
                msg = msg.capitalize()
                st.caption(f"· {msg}")

        if changed:
            # Show just filenames, not full paths
            filenames = [f.split("/")[-1] for f in changed]
            st.markdown(
                '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#5b20e0;margin:8px 0 4px;">Open files</p>',
                unsafe_allow_html=True,
            )
            st.caption(", ".join(filenames))
    except Exception:
        st.caption("No workspace detected.")

    if st.session_state.tokens_actual > 0:
        saved = st.session_state.tokens_naive - st.session_state.tokens_actual
        pct = int(saved / st.session_state.tokens_naive * 100) if st.session_state.tokens_naive else 0
        st.divider()
        st.markdown("### Token savings")
        st.markdown(
            f'<div style="background:#f3f0ff;border-radius:8px;padding:10px 12px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            f'<span style="font-size:0.75rem;color:#656565;">Sent with Memori</span>'
            f'<span style="font-size:0.75rem;font-weight:600;color:#292929;">{st.session_state.tokens_actual:,}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
            f'<span style="font-size:0.75rem;color:#656565;">Without Memori</span>'
            f'<span style="font-size:0.75rem;font-weight:600;color:#989898;text-decoration:line-through;">{st.session_state.tokens_naive:,}</span>'
            f'</div>'
            f'<div style="border-top:1px solid #ede9fe;padding-top:8px;display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:0.75rem;font-weight:700;color:#712fff;">Saved</span>'
            f'<span style="font-size:0.9rem;font-weight:700;color:#712fff;">{pct}% &nbsp;·&nbsp; {saved:,} tokens</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:2rem;">
    <h1 style="margin:0 0 6px;font-size:1.85rem;font-weight:700;color:#0B0C0D;letter-spacing:-0.025em;">
        Persistent Memory Dev Agent
    </h1>
    <p style="margin:0;color:#656565;font-size:0.95rem;">
        Four specialized agents · branch-scoped memory · zero manual context
    </p>
</div>
""", unsafe_allow_html=True)

# ── Task input ────────────────────────────────────────────────────────────────
st.markdown("""
<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
           text-transform:uppercase;color:#5b20e0;margin-bottom:6px;">Task</p>
""", unsafe_allow_html=True)

# Apply any pending example selection before the widget renders — must happen
# before key="task_area" is instantiated or Streamlit raises StreamlitAPIException
if st.session_state.get("pending_task"):
    st.session_state.task_area = st.session_state.pop("pending_task")

task = st.text_area(
    "task_input",
    placeholder='Describe the task — e.g. "Add a retry mechanism so failed API calls recover automatically" or "Find edge cases in the checkout flow before we ship"',
    height=110,
    label_visibility="collapsed",
    key="task_area",
)

col_btn, col_pills, _ = st.columns([1, 3, 2])
with col_btn:
    run_btn = st.button("Run Agents", type="primary", disabled=not task.strip(), use_container_width=True)
with col_pills:
    if selected_agents:
        pills_html = "".join(
            f'<span style="font-size:0.7rem;color:{c};background:{c}15;'
            f'padding:2px 9px;border-radius:100px;font-weight:500;white-space:nowrap;">{e} {n}</span> '
            for n, _, e, c in PIPELINE if n in selected_agents
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;height:38px;flex-wrap:wrap;">{pills_html}</div>',
            unsafe_allow_html=True,
        )

# ── Example prompts ───────────────────────────────────────────────────────────
st.markdown("""
<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
           text-transform:uppercase;color:#5b20e0;margin:1.4rem 0 0.5rem;">Try an example</p>
""", unsafe_allow_html=True)
eg_cols = st.columns(3)
for i, prompt in enumerate(EXAMPLE_PROMPTS):
    if eg_cols[i % 3].button(prompt, key=f"eg_{i}", use_container_width=True):
        st.session_state["pending_task"] = prompt
        st.rerun()

# ── Pipeline diagram (shown before first run) ─────────────────────────────────
if st.session_state.tokens_actual == 0:
    agent_cards_html = ""
    for idx, (name, _, emoji, color) in enumerate(PIPELINE):
        agent_cards_html += (
            f'<div style="flex:1;background:#fff;border:1.5px solid #ede9fe;border-radius:10px;'
            f'padding:18px 12px;text-align:center;border-top:3px solid {color};">'
            f'<div style="font-size:1.3rem;line-height:1;margin-bottom:7px;">{emoji}</div>'
            f'<div style="font-weight:700;font-size:0.86rem;color:#0B0C0D;">{name}</div>'
            f'<div style="font-size:0.75rem;color:#656565;margin-top:4px;line-height:1.4;">'
            f'{AGENT_DESCRIPTIONS[name]}</div></div>'
        )
        if idx < len(PIPELINE) - 1:
            agent_cards_html += (
                '<div style="display:flex;align-items:center;padding:0 6px;'
                'color:#c4b5fd;font-size:1.1rem;flex-shrink:0;margin-top:-10px;">→</div>'
            )
    st.markdown(f"""
<div style="margin:2.2rem 0 0.5rem;">
  <p style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
            color:#5b20e0;margin-bottom:0.9rem;">How it works</p>
  <div style="display:flex;gap:0;align-items:flex-start;">{agent_cards_html}</div>
  <div style="text-align:center;margin-top:14px;font-size:0.78rem;color:#656565;">
    All agents share <strong style="color:#712fff;">branch-scoped memory</strong>
    — decisions, findings, and patterns persist across sessions automatically.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Swarm execution ───────────────────────────────────────────────────────────
if run_btn and task.strip():
    if not selected_agents:
        st.error("Select at least one agent in the sidebar.")
        st.stop()

    apply_keys(provider_label, memori_key, llm_key, llm_key2, model, region_val)
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

    results: dict[str, str] = {}
    prior_output = ""
    active = [(n, cls, e, c) for n, cls, e, c in PIPELINE if n in selected_agents]
    slots = {name: st.empty() for name, *_ in active}
    run_prompt_tokens = 0

    for name, agent_cls, emoji, color in active:
        slots[name].markdown(
            f'<div style="border:1.5px solid #ede9fe;border-radius:10px;background:#fff;'
            f'box-shadow:0 2px 8px rgba(113,47,255,0.05);margin-bottom:10px;">'
            + agent_header_html(name, emoji, color, thinking=True)
            + '<p style="color:#6d28d9;font-size:0.85rem;font-style:italic;padding-bottom:12px;">Running…</p>'
            + "</div></div>",
            unsafe_allow_html=True,
        )

        try:
            agent = agent_cls()
            output = agent.run(task=task, prior_context=prior_output)
            run_prompt_tokens += agent.last_prompt_tokens
            results[name] = output
            prior_output = output
        except Exception as e:
            slots[name].markdown(
                f'<div style="border:1.5px solid #fee2e2;border-radius:10px;background:#fff;margin-bottom:10px;">'
                + agent_header_html(name, emoji, "#ff3f16")
                + f'<p style="color:#ff3f16;font-size:0.85rem;">{e}</p>'
                + "</div></div>",
                unsafe_allow_html=True,
            )
            break

        with slots[name].container():
            st.markdown(
                f'<div style="border:1.5px solid #ede9fe;border-radius:10px;background:#fff;'
                f'box-shadow:0 2px 8px rgba(113,47,255,0.05);margin-bottom:10px;overflow:hidden;">'
                + agent_header_html(name, emoji, color)
                + "</div></div>",
                unsafe_allow_html=True,
            )
            with st.container():
                st.markdown(output)

    if results:
        # Update token savings counters.
        # Naive cost = what we actually sent + all prior run outputs we're NOT re-sending.
        prior_chars = st.session_state.accumulated_output_chars
        naive_this_run = run_prompt_tokens + prior_chars // 4  # chars/4 ≈ tokens
        st.session_state.tokens_actual += run_prompt_tokens
        st.session_state.tokens_naive += max(naive_this_run, run_prompt_tokens)
        st.session_state.accumulated_output_chars += sum(len(v) for v in results.values())

        st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
        st.success("Done — context saved to Memori. Your next session picks up exactly here.")
        with st.expander("Export results"):
            full_md = "\n\n---\n\n".join(f"## {n}\n\n{out}" for n, out in results.items())
            st.download_button(
                "⬇  Download Markdown",
                data=full_md,
                file_name=f"agents-{task[:40].replace(' ', '-')}.md",
                mime="text/markdown",
            )
