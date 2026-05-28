"""
AI Consultant Agent with Memori
Streamlit interface for AI readiness assessment + memory-powered follow-ups.
Supports OpenAI, Google Gemini, and Anthropic Claude as LLM backends.
"""

import base64
import os

import streamlit as st
from dotenv import load_dotenv
from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from workflow import CompanyProfile, _llm_completion, run_ai_assessment

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

load_dotenv()

st.set_page_config(page_title="AI Consultant Agent", layout="wide")

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "claude": "Anthropic Claude",
}
_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}
_PROVIDER_KEY_LABELS = {
    "openai": "OpenAI API Key",
    "gemini": "Gemini API Key",
    "claude": "Anthropic API Key",
}


def _load_inline_image(path: str, height_px: int) -> str:
    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return (
            f"<img src='data:image/png;base64,{encoded}' "
            f"style='height:{height_px}px; width:auto; display:inline-block; "
            f"vertical-align:middle; margin:0 8px;' alt='Logo'>"
        )
    except Exception:
        return ""


memori_img_inline = _load_inline_image("assets/Memori_Logo.png", height_px=90)
tavily_img_inline = _load_inline_image("assets/tavily_logo.png", height_px=70)

title_html = f"""
<div style='display:flex; align-items:center; width:120%; padding:8px 0;'>
  <h1 style='margin:0; padding:0; font-size:2.5rem; font-weight:800; display:flex; align-items:center; gap:5px;'>
    <span>AI Consultant Agent with</span>
    {memori_img_inline}and
    {tavily_img_inline}
  </h1>
</div>
"""
st.markdown(title_html, unsafe_allow_html=True)


def _init_memori(provider: str, api_key: str) -> None:
    """Initialize Memori + LLM client and store both in session state."""
    if not api_key:
        st.warning(
            f"{_PROVIDER_KEY_LABELS[provider]} is not set – Memori will not be active."
        )
        return
    try:
        db_path = os.getenv("SQLITE_DB_PATH", "./memori.sqlite")
        engine = create_engine(
            f"sqlite:///{db_path}",
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        if provider == "claude":
            from anthropic import Anthropic

            claude_client = Anthropic(api_key=api_key)
            mem = Memori(conn=SessionLocal).anthropic.register(claude_client)
            st.session_state.claude_client = claude_client
            st.session_state.openai_client = None
        else:
            if provider == "gemini":
                client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
            else:
                client = OpenAI(api_key=api_key)
            mem = Memori(conn=SessionLocal).openai.register(client)
            st.session_state.openai_client = client
            st.session_state.claude_client = None

        mem.attribution(entity_id="ai-consultant-user", process_id="ai-consultant")
        if mem.config.storage is not None:
            mem.config.storage.build()

        st.session_state.memori = mem
        st.session_state.llm_provider = provider
        st.session_state.api_key = api_key
    except Exception as e:
        st.warning(f"Memori initialization note: {e}")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🔑 API Keys")

    provider = st.selectbox(
        "LLM Provider",
        options=["openai", "gemini", "claude"],
        format_func=lambda p: _PROVIDER_LABELS[p],
        index=0,
    )

    env_key = _PROVIDER_KEY_ENV[provider]
    api_key_input = st.text_input(
        _PROVIDER_KEY_LABELS[provider],
        value=os.getenv(env_key, ""),
        type="password",
    )

    memori_api_key_input = st.text_input(
        "Memori API Key (optional)",
        value=os.getenv("MEMORI_API_KEY", ""),
        type="password",
        help="Used for Memori Advanced Augmentation and higher quotas.",
    )

    tavily_api_key_input = st.text_input(
        "Tavily API Key",
        value=os.getenv("TAVILY_API_KEY", ""),
        type="password",
        help="Your Tavily API key for web/case-study search",
    )

    if st.button("Save API Keys"):
        if api_key_input:
            os.environ[env_key] = api_key_input
        if memori_api_key_input:
            os.environ["MEMORI_API_KEY"] = memori_api_key_input
        if tavily_api_key_input:
            os.environ["TAVILY_API_KEY"] = tavily_api_key_input
        _init_memori(provider, api_key_input)
        st.success("✅ API keys saved for this session")

    effective_key = api_key_input or os.getenv(env_key, "")
    both_keys_present = bool(os.getenv("TAVILY_API_KEY")) and bool(effective_key)
    if both_keys_present:
        st.caption("Both API keys detected ✅")
    else:
        st.caption("Missing API keys – some features may not work ⚠️")

    st.markdown("---")
    st.markdown("### 💡 About")
    st.markdown(
        """
        This application acts as an *AI consultant* for companies:
        - Assesses *AI readiness* and where to integrate AI.
        - Suggests *use cases* across workforce, tools, and ecosystem.
        - Provides rough *cost bands* and risks.
        - Uses *Memori* to remember past assessments and Q&A.

        Web research is powered by *Tavily*. Supports **OpenAI**, **Gemini**, and **Claude**.

        ---

        Made with ❤️ by [Studio1](https://www.Studio1hq.com) Team
        """
    )

# ── Session state init ────────────────────────────────────────────────────────
if "assessment_markdown" not in st.session_state:
    st.session_state.assessment_markdown = None
if "company_profile" not in st.session_state:
    st.session_state.company_profile = None
if "memory_messages" not in st.session_state:
    st.session_state.memory_messages = []

# Initialize Memori once on first load
if "memori" not in st.session_state:
    initial_key = api_key_input or os.getenv(env_key, "")
    if initial_key:
        _init_memori(provider, initial_key)

# ── Guards ────────────────────────────────────────────────────────────────────
tavily_key = os.getenv("TAVILY_API_KEY", "")
if not tavily_key:
    st.warning("⚠️ Please enter your Tavily API key in the sidebar to run assessments!")
    st.stop()

effective_key = api_key_input or os.getenv(env_key, "")
if not effective_key:
    st.warning(
        f"⚠️ {_PROVIDER_KEY_LABELS[provider]} missing – LLM responses will not work."
    )
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 AI Assessment", "🧠 Memory"])

with tab1:
    st.markdown("#### Configure Company Profile & AI Assessment")

    col1, col2 = st.columns([2, 1])
    with col1:
        company_name = st.text_input("Company Name *", placeholder="e.g., Acme Corp")
        industry = st.text_input(
            "Industry *", placeholder="e.g., Retail, Fintech, Manufacturing"
        )
        region = st.text_input(
            "Region / Market", placeholder="e.g., US, EU, Global, APAC"
        )
    with col2:
        company_size = st.selectbox(
            "Company Size *", options=["1-50", "51-200", "201-1000", "1000+"]
        )
        tech_maturity = st.selectbox(
            "Tech & Data Maturity *", options=["Low", "Medium", "High"]
        )

    goals = st.multiselect(
        "Business Goals for AI",
        options=[
            "Cost reduction",
            "Revenue growth",
            "Customer experience",
            "Operational efficiency",
            "Risk & compliance",
            "Innovation / new products",
        ],
    )
    ai_focus_areas = st.multiselect(
        "AI Focus Areas",
        options=[
            "Internal workflows & automation",
            "Customer support / CX",
            "Analytics & BI",
            "Product features",
            "Partner ecosystem / APIs",
        ],
    )

    col3, col4 = st.columns(2)
    with col3:
        budget_range = st.selectbox(
            "Rough Budget Range *",
            options=["< $50k", "$50k-$250k", "$250k-$1M", ">$1M"],
        )
    with col4:
        time_horizon = st.selectbox(
            "Time Horizon for Initial Rollout *",
            options=["0-3 months", "3-6 months", "6-12 months", "12+ months"],
        )

    notes = st.text_area(
        "Additional Notes",
        placeholder="Any constraints, existing systems, or regulatory considerations.",
        height=120,
    )

    run_assessment = st.button("📊 Run AI Assessment", type="primary")

    if run_assessment:
        if not company_name or not industry:
            st.error("Please provide at least a company name and industry.")
        else:
            try:
                profile = CompanyProfile(
                    company_name=company_name.strip(),
                    industry=industry.strip(),
                    company_size=company_size,
                    region=region.strip() if region else None,
                    tech_maturity=tech_maturity,
                    goals=goals,
                    ai_focus_areas=ai_focus_areas,
                    budget_range=budget_range,
                    time_horizon=time_horizon,
                    notes=notes.strip() if notes else None,
                )
            except Exception as e:
                st.error(f"Invalid configuration: {e}")
            else:
                with st.spinner("🤖 Running AI assessment (research + reasoning)..."):
                    try:
                        assessment_markdown, _snippets = run_ai_assessment(
                            profile,
                            provider=provider,
                            api_key=effective_key,
                        )
                        st.session_state.assessment_markdown = assessment_markdown
                        st.session_state.company_profile = profile
                        st.markdown(
                            f"## 🧾 AI Readiness & Cost Assessment for *{profile.company_name}*"
                        )
                        st.markdown(assessment_markdown)
                    except Exception as e:
                        st.error(f"❌ Error during assessment: {e}")

    if st.session_state.assessment_markdown and not run_assessment:
        st.markdown(
            "### Last Assessment Result "
            + (
                f"for *{st.session_state.company_profile.company_name}*"
                if st.session_state.company_profile
                else ""
            )
        )
        st.markdown(st.session_state.assessment_markdown)

with tab2:
    st.markdown("#### Ask about past AI assessments")

    if st.session_state.company_profile:
        st.info(
            f"Most recent company: *{st.session_state.company_profile.company_name}* "
            f"({st.session_state.company_profile.industry})"
        )
    else:
        st.info(
            "Run at least one assessment in the *AI Assessment* tab to ground the memory context."
        )

    for message in st.session_state.memory_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    memory_prompt = st.chat_input("Ask about past AI assessments (Memori-powered)…")

    if memory_prompt:
        st.session_state.memory_messages.append(
            {"role": "user", "content": memory_prompt}
        )
        with st.chat_message("user"):
            st.markdown(memory_prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking…"):
                try:
                    latest_context = ""
                    if (
                        st.session_state.assessment_markdown
                        and st.session_state.company_profile
                    ):
                        p = st.session_state.company_profile
                        latest_context = (
                            f"\n\nLatest assessment summary for {p.company_name} "
                            f"({p.industry}, {p.company_size}, {p.tech_maturity} tech maturity):\n"
                            f"{st.session_state.assessment_markdown[:1500]}\n"
                        )

                    system = (
                        "You are an AI consultant assistant with access to stored AI readiness assessments. "
                        "Answer questions about past recommendations, cost bands, risks, and next steps. "
                        "If asked outside this scope, politely say you only answer about AI consulting.\n"
                        + latest_context
                    )

                    response_text = _llm_completion(
                        system, memory_prompt, provider, effective_key
                    )

                    st.session_state.memory_messages.append(
                        {"role": "assistant", "content": response_text}
                    )
                    st.markdown(response_text)
                except Exception as e:
                    err = f"❌ Error: {e}"
                    st.session_state.memory_messages.append(
                        {"role": "assistant", "content": err}
                    )
                    st.error(err)
