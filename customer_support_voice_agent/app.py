"""
Customer Support Voice Agent with Memori v3

Streamlit app:
- Single chat interface for customer support on top of your own docs/FAQs.
- Uses Memori v3 for memory, with OpenAI, Gemini, or Claude as the LLM backend.
- TTS voice output is only available when using the OpenAI provider.

Prereqs:
- Set the API key for your chosen provider (OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY).
- Set FIRECRAWL_API_KEY to ingest documentation URLs into Memori.
"""

import base64
import os
from io import BytesIO
from typing import Any, cast

import streamlit as st
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

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


def _init_memori(provider: str, api_key: str) -> Memori | None:
    """Initialize Memori v3 with the chosen LLM provider."""
    if not api_key:
        st.warning(
            f"{_PROVIDER_KEY_LABELS[provider]} is not set – Memori v3 will not be active."
        )
        return None
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

        mem.attribution(
            entity_id="customer-support-user", process_id="customer-support"
        )
        if mem.config.storage is not None:
            mem.config.storage.build()

        st.session_state.memori = mem
        st.session_state.llm_provider = provider
        st.session_state.api_key = api_key
        return mem
    except Exception as e:
        st.warning(f"Memori v3 initialization note: {e}")
        return None


def _llm_completion(system: str, user: str, provider: str, api_key: str) -> str:
    """Route a chat completion through the selected LLM provider."""
    if provider == "claude":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""))
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text  # type: ignore[union-attr]

    model = (
        os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        if provider == "gemini"
        else os.getenv("SUPPORT_MODEL", "gpt-4o-mini")
    )
    openai_client: OpenAI = st.session_state.openai_client
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def _synth_audio(text: str) -> BytesIO | None:
    """Call OpenAI TTS to synthesize speech. Only available for OpenAI provider."""
    client: OpenAI | None = st.session_state.get("openai_client")
    if client is None:
        return None
    try:
        result = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio_bytes = result.read() if hasattr(result, "read") else result
        if isinstance(audio_bytes, bytes):
            return BytesIO(audio_bytes)
        return None
    except Exception as e:
        st.warning(f"TTS error: {e}")
        return None


def _ingest_urls_with_firecrawl(
    mem: Memori, provider: str, api_key: str, urls: list[str]
) -> int:
    """Ingest documentation URLs into Memori using Firecrawl."""
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not firecrawl_key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set – cannot ingest docs.")

    app = FirecrawlApp(api_key=firecrawl_key)
    all_pages = []

    for base_url in urls:
        try:
            job = app.crawl(
                base_url,
                limit=50,
                scrape_options={
                    "formats": ["markdown", "html"],
                    "onlyMainContent": True,
                },
            )
            if isinstance(job, dict):
                pages = job.get("data") or job.get("pages") or job
            else:
                pages = (
                    getattr(job, "data", None)
                    or getattr(job, "pages", None)
                    or getattr(job, "results", None)
                )
                if pages is None:
                    if hasattr(job, "model_dump"):
                        data = job.model_dump()
                    elif hasattr(job, "dict"):
                        data = job.dict()
                    else:
                        data = job
                    pages = (
                        data.get("data")
                        or data.get("pages")
                        or data.get("results")
                        or data
                    )

            if isinstance(pages, list):
                all_pages.extend(pages)
            elif isinstance(pages, dict):
                all_pages.append(pages)
        except Exception as e:
            st.warning(f"Firecrawl issue while crawling {base_url}: {e}")

    dedup_pages = []
    seen_urls: set = set()
    for page in all_pages:
        url = None
        if isinstance(page, dict):
            meta = page.get("metadata") or {}
            url = page.get("url") or meta.get("sourceURL")
        key = url or id(page)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        dedup_pages.append(page)

    company_name = st.session_state.get("company_name") or "the company"
    ingested = 0

    for idx, page in enumerate(dedup_pages, start=1):
        if isinstance(page, dict):
            page_dict = page
        else:
            if hasattr(page, "model_dump"):
                page_dict = cast(Any, page).model_dump()
            elif hasattr(page, "dict"):
                page_dict = cast(Any, page).dict()
            else:
                continue

        metadata = page_dict.get("metadata") or {}
        url = page_dict.get("url") or metadata.get("sourceURL") or urls[0]
        markdown = (
            page_dict.get("markdown")
            or page_dict.get("text")
            or page_dict.get("content")
            or ""
        )
        if not markdown:
            continue
        title = page_dict.get("title") or metadata.get("title") or f"Page {idx}"

        doc_text = f"""{company_name} Documentation Page
Title: {title}
URL: {url}

Content:
{markdown}
"""
        ingest_prompt = (
            "Store the following documentation page in memory for "
            "future customer-support conversations. Respond with a "
            f"short acknowledgement only.\n\n{doc_text}"
        )

        try:
            if provider == "claude":
                from anthropic import Anthropic

                claude = Anthropic(
                    api_key=api_key or os.getenv("ANTHROPIC_API_KEY", "")
                )
                claude.messages.create(
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                    max_tokens=128,
                    messages=[{"role": "user", "content": ingest_prompt}],
                )
            else:
                model = (
                    os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
                    if provider == "gemini"
                    else "gpt-4o-mini"
                )
                openai_client: OpenAI = st.session_state.openai_client
                openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": ingest_prompt}],
                )
            ingested += 1
        except Exception as e:
            st.warning(f"Memori ingestion issue for {url}: {e}")

    try:
        adapter = getattr(mem.config.storage, "adapter", None)
        if adapter is not None:
            adapter.commit()
    except Exception as e:
        st.warning(f"Memori commit note: {e}")

    return ingested


def main():
    st.set_page_config(page_title="Customer Support Voice Agent", layout="wide")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""

    memori_img_inline = _load_inline_image(
        "../job_search_agent/assets/Memori_Logo.png", height_px=90
    )
    title_html = f"""
<div style='display:flex; align-items:center; width:120%; padding:8px 0;'>
  <h1 style='margin:0; padding:0; font-size:2.2rem; font-weight:800; display:flex; align-items:center; gap:10px;'>
    <span>Customer Support Voice Agent with</span>
    {memori_img_inline}
  </h1>
</div>
"""
    st.markdown(title_html, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("🔑 API & Storage")

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

        if provider != "openai":
            st.caption("ℹ️ Voice (TTS) output requires the OpenAI provider.")

        firecrawl_api_key_input = st.text_input(
            "Firecrawl API Key",
            value=os.getenv("FIRECRAWL_API_KEY", ""),
            type="password",
            help="Used to crawl/scrape your documentation URLs into Memori.",
        )

        memori_api_key_input = st.text_input(
            "Memori API Key (optional)",
            value=os.getenv("MEMORI_API_KEY", ""),
            type="password",
            help="Used for Memori Advanced Augmentation and higher quotas.",
        )

        company_name_input = st.text_input(
            "Company Name (optional)",
            value=st.session_state.company_name,
            help="Used to personalize prompts and titles.",
        )
        st.session_state.company_name = company_name_input.strip()

        if st.button("Save Settings"):
            if api_key_input:
                os.environ[env_key] = api_key_input
            if firecrawl_api_key_input:
                os.environ["FIRECRAWL_API_KEY"] = firecrawl_api_key_input
            if memori_api_key_input:
                os.environ["MEMORI_API_KEY"] = memori_api_key_input
            st.success("✅ Settings saved. Re-initializing Memori…")
            _init_memori(provider, api_key_input)

        st.markdown("---")
        st.markdown("### 📚 Ingest Docs into Memori")
        ingest_urls_text = st.text_area(
            "Documentation URLs (one per line)",
            placeholder="https://docs.yourcompany.com\nhttps://yourcompany.com/help",
            height=140,
        )
        if st.button("Extract & store to Memori"):
            urls = [u.strip() for u in ingest_urls_text.splitlines() if u.strip()]
            mem = st.session_state.get("memori")
            effective_key = api_key_input or os.getenv(env_key, "")
            if not urls:
                st.warning("Please enter at least one URL to ingest.")
            elif mem is None:
                st.warning("Memori not initialized – check your API key above.")
            else:
                try:
                    count = _ingest_urls_with_firecrawl(
                        mem, provider, effective_key, urls
                    )
                    st.success(
                        f"✅ Ingested {count} documentation page(s) into Memori."
                    )
                except Exception as e:
                    st.error(f"❌ Ingestion error: {e}")

        st.markdown("---")
        st.markdown("### 💡 About the Agent")
        st.markdown(
            """
            This agent answers customer-support questions for **your own product or company**:
            - Docs, FAQs, services, pricing, and onboarding flows
            - Product capabilities and common troubleshooting steps

            Knowledge is built from documentation URLs ingested via **Firecrawl** and stored in **Memori v3**.

            Supports **OpenAI**, **Gemini**, and **Claude**. Voice (TTS) requires OpenAI.
            """
        )

    # ── Init Memori on first run ──────────────────────────────────────────────
    if "memori" not in st.session_state:
        initial_key = api_key_input or os.getenv(env_key, "")
        if initial_key:
            _init_memori(provider, initial_key)

    effective_key = api_key_input or os.getenv(env_key, "")
    if "memori" not in st.session_state or not effective_key:
        st.warning(
            f"⚠️ {_PROVIDER_KEY_LABELS[provider]} missing or Memori failed to initialize – "
            "LLM responses will not work."
        )
        st.stop()

    mem: Memori = st.session_state.memori

    # ── Voice toggle (OpenAI only) ────────────────────────────────────────────
    col_voice, _ = st.columns([1, 3])
    with col_voice:
        voice_available = provider == "openai"
        enable_voice = st.checkbox(
            "🔊 Enable voice responses",
            value=voice_available,
            disabled=not voice_available,
        )

    # ── Chat history ──────────────────────────────────────────────────────────
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask a customer-support question…")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking with your ingested knowledge…"):
                try:
                    kb_snippets = []
                    try:
                        if hasattr(mem, "search"):
                            kb_snippets = (
                                cast(Any, mem).search(user_input, limit=5) or []
                            )
                    except Exception as search_err:
                        st.warning(f"Memori search issue: {search_err}")

                    kb_context = ""
                    if kb_snippets:
                        kb_context = "Here are some relevant snippets from the company knowledge base:\n"
                        for snip in kb_snippets:
                            kb_context += f"- {snip}\n"

                    company_name = (
                        st.session_state.get("company_name") or "your company"
                    )
                    system_prompt = f"""You are a helpful customer support assistant for {company_name}.

Use ONLY the company's documentation and prior stored content in Memori to answer.
If something is unclear or not covered, say that it isn't in the docs instead of hallucinating.

Context from the knowledge base (may be partial):
{kb_context}
"""

                    answer = _llm_completion(
                        system_prompt, user_input, provider, effective_key
                    )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.markdown(answer)

                    if enable_voice and answer.strip():
                        audio_buf = _synth_audio(answer)
                        if audio_buf is not None:
                            st.audio(audio_buf.getvalue(), format="audio/mp3")
                except Exception as e:
                    err = f"❌ Error generating answer: {e}"
                    st.session_state.messages.append(
                        {"role": "assistant", "content": err}
                    )
                    st.error(err)


if __name__ == "__main__":
    main()
