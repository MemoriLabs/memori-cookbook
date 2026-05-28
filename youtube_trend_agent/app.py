"""
YouTube Trend Analysis Agent with Memori, multi-provider LLM, and YouTube scraping.

Streamlit app:
- Sidebar: LLM provider selector, API keys, YouTube channel URL, ingest button.
- Main: Chat interface to ask about trends and get new video ideas.

Supports OpenAI, Google Gemini, and Anthropic Claude as LLM backends.
"""

import base64
import os

import streamlit as st
from core import fetch_exa_trends, ingest_channel_into_memori, init_memori

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "claude": "Anthropic Claude",
}

_PROVIDER_KEY_LABELS = {
    "openai": "OpenAI API Key",
    "gemini": "Gemini API Key",
    "claude": "Anthropic API Key",
}


def _load_inline_image(path: str, height_px: int) -> str:
    """Return an inline <img> tag for a local PNG, or empty string on failure."""
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


def _run_chat_prompt(full_prompt: str, provider: str, api_key: str) -> str:
    """Route a chat completion through the selected LLM provider."""
    if provider == "claude":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""))
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.content[0].text  # type: ignore

    if provider == "gemini":
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key or os.getenv("GEMINI_API_KEY", ""),
            base_url=GEMINI_BASE_URL,
        )
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.choices[0].message.content or ""

    # OpenAI via Agno
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    model_id = os.getenv("YOUTUBE_TREND_MODEL", "gpt-4o-mini")
    model_kwargs: dict = {"id": model_id}
    if api_key:
        model_kwargs["api_key"] = api_key
    advisor = Agent(
        name="YouTube Trend Advisor",
        model=OpenAIChat(**model_kwargs),
        markdown=True,
    )
    result = advisor.run(full_prompt)
    return str(result.content) if hasattr(result, "content") else str(result)


def main():
    st.set_page_config(
        page_title="YouTube Trend Analysis Agent",
        layout="wide",
    )

    memori_img_inline = _load_inline_image("assets/Memori_Logo.png", height_px=85)
    title_html = f"""
<div style='display:flex; align-items:center; width:120%; padding:8px 0;'>
  <h1 style='margin:0; padding:0; font-size:2.2rem; font-weight:800; display:flex; align-items:center; gap:10px;'>
    <span>YouTube Trend Analysis Agent with</span>
    {memori_img_inline}
  </h1>
</div>
"""
    st.markdown(title_html, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("🔑 API Keys & Channel")

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

        exa_api_key_input = st.text_input(
            "Exa API Key (optional)",
            value=os.getenv("EXA_API_KEY", ""),
            type="password",
            help="Used to fetch external web trends via Exa AI when suggesting new ideas.",
        )

        memori_api_key_input = st.text_input(
            "Memori API Key (optional)",
            value=os.getenv("MEMORI_API_KEY", ""),
            type="password",
            help="Used for Memori Advanced Augmentation and higher quotas.",
        )

        channel_url_input = st.text_input(
            "YouTube channel / playlist URL",
            placeholder="https://www.youtube.com/@YourChannel",
        )

        if st.button("Save Settings"):
            if api_key_input:
                os.environ[env_key] = api_key_input
            if exa_api_key_input:
                os.environ["EXA_API_KEY"] = exa_api_key_input
            if memori_api_key_input:
                os.environ["MEMORI_API_KEY"] = memori_api_key_input

            # Initialize Memori with chosen provider
            st.session_state["api_key"] = api_key_input
            init_memori(provider=provider, api_key=api_key_input)
            st.success("✅ Settings saved for this session.")

        st.markdown("---")

        if st.button("Ingest channel into Memori"):
            effective_key = api_key_input or os.getenv(env_key, "")
            if not effective_key:
                st.warning(
                    f"{_PROVIDER_KEY_LABELS[provider]} is required before ingestion."
                )
            elif not channel_url_input.strip():
                st.warning("Please enter a YouTube channel or playlist URL.")
            else:
                # Ensure session state reflects current sidebar selections
                st.session_state["api_key"] = effective_key
                st.session_state["llm_provider"] = provider
                if st.session_state.get("memori") is None:
                    init_memori(provider=provider, api_key=effective_key)
                with st.spinner(
                    "📥 Scraping channel and ingesting videos into Memori…"
                ):
                    count = ingest_channel_into_memori(channel_url_input.strip())
                st.success(f"✅ Ingested {count} video(s) into Memori.")

        st.markdown("---")
        st.markdown("### 💡 About")
        st.markdown(
            """
            This agent:

            - Scrapes your **YouTube channel** directly from YouTube using yt-dlp.
            - Stores video metadata & summaries in **Memori**.
            - Uses **Exa** and your channel info stored in **Memori** to surface trends and new video ideas.
            """
        )

    # ── Guard: need API key ───────────────────────────────────────────────────
    effective_key = api_key_input or os.getenv(_PROVIDER_KEY_ENV[provider], "")
    if not effective_key:
        st.warning(
            f"⚠️ Please enter your {_PROVIDER_LABELS[provider]} API key in the sidebar to start chatting!"
        )
        st.stop()

    # ── Chat history ──────────────────────────────────────────────────────────
    st.markdown(
        "<h2 style='margin-top:0;'>YouTube Trend Chat</h2>",
        unsafe_allow_html=True,
    )
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    prompt = st.chat_input("Ask about your channel trends or new video ideas…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing your channel memories…"):
                try:
                    memori_context = ""
                    mem = st.session_state.get("memori")
                    if mem is not None and hasattr(mem, "search"):
                        try:
                            results = mem.search(prompt, limit=5)
                            if results:
                                memori_context = (
                                    "\n\nRelevant snippets from your channel history:\n"
                                    + "\n".join(f"- {r}" for r in results)
                                )
                        except Exception as e:
                            st.warning(f"Memori search issue: {e}")

                    videos = st.session_state.get("channel_videos") or []
                    video_summaries = ""
                    if videos:
                        lines = []
                        for v in videos[:10]:
                            title = v.get("title") or "Untitled video"
                            topics = v.get("topics") or []
                            topics_str = ", ".join(topics) if topics else "N/A"
                            views = v.get("views") or "Unknown"
                            desc = v.get("description") or ""
                            desc_snip = (
                                (desc[:120].rstrip() + "…") if len(desc) > 120 else desc
                            )
                            lines.append(
                                f"- {title} | topics: {topics_str} | views: {views} | desc: {desc_snip}"
                            )
                        video_summaries = (
                            "\n\nRecent videos on this channel:\n" + "\n".join(lines)
                        )

                    channel_name = (
                        st.session_state.get("channel_title") or "this YouTube channel"
                    )

                    exa_trends = ""
                    if os.getenv("EXA_API_KEY") and videos:
                        if "exa_trends" in st.session_state:
                            exa_trends = st.session_state["exa_trends"]
                        else:
                            exa_trends = fetch_exa_trends(channel_name, videos)
                            st.session_state["exa_trends"] = exa_trends

                    full_prompt = f"""You are a YouTube strategy assistant analyzing the channel '{channel_name}'.

You have access to a memory store of the user's past videos (titles, topics, views).
Use that memory to:
- Identify topics and formats that perform well on the channel.
- Suggest concrete, fresh video ideas aligned with those trends.
- Optionally point out gaps or under-explored themes.

Always be specific and actionable (titles, angles, hooks, examples), but ONLY answer what the user actually asks.
Do NOT provide long, generic strategy plans unless the user explicitly asks for them.

User question:
{prompt}

Memory context (may be partial):
{memori_context}

Channel metadata from recent scraped videos (titles, topics, views):
{video_summaries}

External web trends for this niche (may be partial):
{exa_trends}
"""

                    response_text = _run_chat_prompt(
                        full_prompt, provider, effective_key
                    )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )
                    st.markdown(response_text)
                except Exception as e:
                    err = f"❌ Error generating answer: {e}"
                    st.session_state.messages.append(
                        {"role": "assistant", "content": err}
                    )
                    st.error(err)


if __name__ == "__main__":
    main()
