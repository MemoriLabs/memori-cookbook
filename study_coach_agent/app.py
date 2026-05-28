import base64
import json
import os

import streamlit as st
from dotenv import load_dotenv
from memory_utils import MemoriManager
from study_graph import (
    LearnerProfile,
    StudyLog,
    run_full_evaluation,
    run_initial_verification,
)

load_dotenv()


st.set_page_config(
    page_title="AI Study Coach with Memori",
    layout="wide",
)


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


# Branded title with Memori logo
memori_img_inline = _load_inline_image(
    "assets/Memori_Logo.png",
    height_px=85,
)
title_html = f"""
<div style='display:flex; align-items:center; width:120%; padding:8px 0;'>
  <h1 style='margin:0; padding:0; font-size:2.2rem; font-weight:800; display:flex; align-items:center; gap:10px;'>
    <span>Study Coach Agent with</span>
    {memori_img_inline}
  </h1>
</div>
"""
st.markdown(title_html, unsafe_allow_html=True)


_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


@st.cache_resource
def get_memori_manager(
    provider: str, api_key: str, db_url: str | None
) -> MemoriManager:
    return MemoriManager(
        provider=provider,
        api_key=api_key,
        db_url=db_url,
        sqlite_path="./memori_study.sqlite",
    )


def _get_quiz_llm_client(memori_mgr: MemoriManager):
    """Return an OpenAI-compatible client for study_graph.py's llm_client calls.

    For Claude, wraps the Anthropic client in a duck-typed adapter so that
    study_graph.py's llm_client.chat.completions.create() calls work.
    """
    if memori_mgr._provider != "claude":
        return memori_mgr._openai_client

    claude_client = memori_mgr._claude_client
    assert claude_client is not None

    class _Msg:
        def __init__(self, text: str) -> None:
            self.content = text

    class _Choice:
        def __init__(self, text: str) -> None:
            self.message = _Msg(text)

    class _Resp:
        def __init__(self, text: str) -> None:
            self.choices = [_Choice(text)]

    class _Completions:
        def create(
            self, messages=None, model=None
        ):  # model arg accepted but we use closure model
            system_msg = ""
            user_msgs = []
            for m in messages or []:
                if m.get("role") == "system":
                    system_msg = m.get("content", "")
                else:
                    user_msgs.append(m)
            resp = claude_client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_msg or None,
                messages=user_msgs,
            )
            return _Resp(resp.content[0].text)

    class _Chat:
        completions = _Completions()

    class _Adapter:
        chat = _Chat()

    return _Adapter()


def _ensure_state():
    if "learner_profile" not in st.session_state:
        st.session_state.learner_profile = None
    if "quiz" not in st.session_state:
        st.session_state.quiz = []
    if "explanation_prompt" not in st.session_state:
        st.session_state.explanation_prompt = ""
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "explanation" not in st.session_state:
        st.session_state.explanation = ""
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "progress_messages" not in st.session_state:
        st.session_state.progress_messages = []


def _maybe_restore_profile_from_memori(memori_mgr: MemoriManager) -> None:
    """
    On fresh app loads (after refresh), try to reconstruct the learner profile
    from Memori so the user doesn't have to re-enter it.
    """
    if st.session_state.learner_profile is not None:
        return

    try:
        system_prompt = (
            "You are an AI study coach with access to a long-term memory store "
            "about a single learner. Using that memory, reconstruct the most "
            "recent learner profile that was described.\n\n"
            "Respond ONLY with a JSON object with the following keys:\n"
            '  "name": string,\n'
            '  "main_goal": string,\n'
            '  "timeframe": string,\n'
            '  "subjects": list of strings,\n'
            '  "weekly_hours": integer,\n'
            '  "preferred_formats": list of strings.\n\n'
            "If you truly have no stored information about the learner, respond "
            "with an empty JSON object: {}"
        )
        raw = memori_mgr._chat(
            system=system_prompt,
            user="Return the last known learner profile now.",
        )
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return

        data = json.loads(raw[start : end + 1])
        if not isinstance(data, dict) or not data:
            return

        # Build LearnerProfile; if it fails, just ignore and keep requiring manual entry
        profile = LearnerProfile(
            name=str(data.get("name", "")).strip(),
            main_goal=str(data.get("main_goal", "")).strip(),
            timeframe=str(data.get("timeframe", "")).strip(),
            subjects=[
                str(s).strip() for s in data.get("subjects", []) if str(s).strip()
            ],
            weekly_hours=int(data.get("weekly_hours", 1) or 1),
            preferred_formats=[
                str(f).strip()
                for f in data.get("preferred_formats", [])
                if str(f).strip()
            ],
        )
        # Basic sanity check: require at least a name and goal
        if profile.name and profile.main_goal:
            st.session_state.learner_profile = profile
    except Exception:
        # Fail silently; user can always re-enter profile if needed.
        return


def sidebar_keys():
    with st.sidebar:
        st.subheader("🔑 LLM Provider")
        provider = st.selectbox(
            "Provider",
            options=["OpenAI", "Gemini", "Claude"],
            index=0,
            help="Which LLM provider to use for memory and quiz generation.",
        ).lower()

        env_key = _PROVIDER_KEY_ENV.get(provider, "OPENAI_API_KEY")
        api_key_input = st.text_input(
            f"{provider.capitalize()} API Key",
            value=os.getenv(env_key, ""),
            type="password",
        )

        memori_api_key_input = st.text_input(
            "Memori API Key (optional)",
            value=os.getenv("MEMORI_API_KEY", ""),
            type="password",
            help="Used for Memori Advanced Augmentation and higher quotas.",
        )
        db_url_input = st.text_input(
            "Database URL (optional)",
            value=os.getenv("MEMORI_DB_URL", ""),
            help=(
                "SQLAlchemy or MongoDB URL. "
                "Examples: sqlite:///memori_study.sqlite, "
                "postgresql+psycopg://user:password@host:5432/database, "
                "mongodb://host:27017/memori"
            ),
        )

        if st.button("Save Settings"):
            if api_key_input:
                os.environ[env_key] = api_key_input
            if memori_api_key_input:
                os.environ["MEMORI_API_KEY"] = memori_api_key_input
            if db_url_input:
                os.environ["MEMORI_DB_URL"] = db_url_input

            if api_key_input or memori_api_key_input or db_url_input:
                st.success("✅ Settings saved for this session")
            else:
                st.warning("Please enter at least one API key")

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown(
            """
            This is an **AI Study Coach** demo built for Memori:

            - Plans and tracks study sessions.
            - Uses **LangGraph** to verify understanding with quizzes + explanations.
            - Uses **Memori v3** as long-term learning memory.
            """
        )
        os.environ["_STUDY_PROVIDER"] = provider


def study_plan_tab(memori_mgr: MemoriManager):
    st.markdown("#### 🧭 Study Plan & Learner Profile")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name or handle", placeholder="e.g. 3rdSon")
            main_goal = st.text_input(
                "Main goal",
                placeholder="e.g. Pass AWS SAA, master LangGraph, finish CS50",
            )
            timeframe = st.text_input(
                "Timeframe",
                placeholder="e.g. 3 months, 6 weeks",
            )
        with col2:
            weekly_hours = st.number_input(
                "Planned study hours per week", min_value=1, max_value=80, value=7
            )
            subjects = st.text_input(
                "Subjects / topics (comma-separated)",
                placeholder="e.g. LangGraph, Memori, algorithms",
            )
            preferred_formats = st.multiselect(
                "Preferred learning formats",
                options=[
                    "videos",
                    "docs",
                    "practice problems",
                    "flashcards",
                    "projects",
                ],
            )

        submitted = st.form_submit_button("Save Profile")

    if submitted:
        if not name or not main_goal or not timeframe:
            st.error("Please fill in at least name, main goal, and timeframe.")
            return
        profile = LearnerProfile(
            name=name.strip(),
            main_goal=main_goal.strip(),
            timeframe=timeframe.strip(),
            subjects=[s.strip() for s in subjects.split(",") if s.strip()],
            weekly_hours=weekly_hours,
            preferred_formats=preferred_formats,
        )
        st.session_state.learner_profile = profile

        # Log structured profile into Memori so it can be recalled later
        try:
            memori_mgr.log_learner_profile(profile.model_dump())
            st.success("✅ Profile saved and stored in Memori.")
        except Exception as e:
            st.warning(f"Profile saved in session, but Memori logging failed: {e}")

    if st.session_state.learner_profile:
        p: LearnerProfile = st.session_state.learner_profile
        st.markdown("##### Current Profile")
        st.write(
            {
                "name": p.name,
                "goal": p.main_goal,
                "timeframe": p.timeframe,
                "subjects": p.subjects,
                "weekly_hours": p.weekly_hours,
                "preferred_formats": p.preferred_formats,
            }
        )


def today_session_tab(memori_mgr: MemoriManager):
    st.markdown("#### 📅 Today’s Study Session")

    profile: LearnerProfile | None = st.session_state.learner_profile
    if not profile:
        st.info("Set up your study profile first in the **Study Plan** tab.")
        return

    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input(
            "What did you study today?", placeholder="e.g. LangGraph basics"
        )
        duration = st.number_input(
            "How many minutes did you study?",
            min_value=5,
            max_value=600,
            value=45,
        )
        resource_type = st.selectbox(
            "Main resource type",
            options=["video", "article", "course", "problems", "other"],
        )
    with col2:
        perceived_difficulty = st.selectbox(
            "How difficult was it?",
            options=["easy", "medium", "hard"],
        )
        mood = st.text_input(
            "How did you feel?",
            placeholder="e.g. focused, tired, motivated, frustrated",
        )
        notes = st.text_area("Any additional notes?", height=80)

    if st.button("Generate quiz & explanation check", type="primary"):
        if not topic:
            st.error("Please enter what you studied today.")
            return

        log = StudyLog(
            topic=topic.strip(),
            duration_minutes=duration,
            resource_type=resource_type,
            perceived_difficulty=perceived_difficulty,
            mood=mood.strip() or None,
            free_notes=notes.strip() or None,
        )
        try:
            mgr = memori_mgr  # alias
            initial = run_initial_verification(
                profile=profile, log=log, llm_client=_get_quiz_llm_client(mgr)
            )
            st.session_state.quiz = initial.quiz
            st.session_state.explanation_prompt = initial.explanation_prompt
            st.session_state.answers = ["" for _ in initial.quiz]
            st.session_state.explanation = ""
            st.session_state.current_log = log
        except Exception as e:
            st.error(f"Failed to generate quiz: {e}")

    # Show quiz if available
    quiz = st.session_state.quiz
    if quiz:
        st.markdown("##### 🧪 Quick Understanding Check")
        new_answers: list[str] = []
        for i, q in enumerate(quiz):
            ans = st.text_area(
                f"Q{i + 1}. {q.question}",
                value=(
                    st.session_state.answers[i]
                    if i < len(st.session_state.answers)
                    else ""
                ),
                height=80,
            )
            new_answers.append(ans)
        st.session_state.answers = new_answers

        st.markdown("##### ✍️ Explain in your own words")
        st.session_state.explanation = st.text_area(
            "Explanation",
            value=st.session_state.explanation,
            placeholder=st.session_state.explanation_prompt,
            height=160,
        )

        if st.button("Evaluate my understanding", type="secondary"):
            try:
                mgr = memori_mgr
                log: StudyLog = st.session_state.current_log
                result = run_full_evaluation(
                    profile=profile,
                    log=log,
                    user_quiz_answers=st.session_state.answers,
                    user_explanation=st.session_state.explanation,
                    llm_client=_get_quiz_llm_client(mgr),
                )
                st.session_state.last_result = result

                # Log study session into Memori
                summary = (
                    f"Study session summary:\n"
                    f"- Topic: {log.topic}\n"
                    f"- Duration (min): {log.duration_minutes}\n"
                    f"- Resource: {log.resource_type}\n"
                    f"- Difficulty: {log.perceived_difficulty}\n"
                    f"- Mood: {log.mood or 'N/A'}\n"
                    f"- Score: {result.score}\n"
                    f"- Feedback: {result.feedback or ''}\n"
                    f"- Next step: {result.next_step_recommendation or ''}"
                )
                mgr.log_study_session(summary)

            except Exception as e:
                st.error(f"Failed to evaluate and log session: {e}")

    # Show last result
    if st.session_state.last_result:
        r = st.session_state.last_result
        st.markdown("##### 🎯 Result")
        if r.score is not None:
            st.metric("Understanding score", f"{r.score}/100")
        if r.feedback:
            st.markdown("**Feedback**")
            st.write(r.feedback)
        if r.next_step_recommendation:
            st.markdown("**Recommended next step**")
            st.write(r.next_step_recommendation)


def progress_tab(memori_mgr: MemoriManager):
    st.markdown("#### 📈 Progress & Memory (Memori-powered)")
    st.markdown(
        "Ask questions about your learning history, weak/strong topics, or patterns.\n\n"
        "Examples:\n"
        "- *What are my weakest topics right now?*\n"
        "- *When do I usually perform best?*\n"
        "- *Do I learn better from videos or practice problems?*"
    )

    # Display chat history
    for message in st.session_state.progress_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    prompt = st.chat_input("Ask about your learning progress…")
    if prompt:
        # User message
        st.session_state.progress_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant response via Memori
        with st.chat_message("assistant"):
            with st.spinner("🔍 Checking your study memories…"):
                try:
                    answer = memori_mgr.summarize_progress(prompt)
                    st.session_state.progress_messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.markdown(answer)
                except Exception as e:
                    err = f"❌ Failed to query Memori: {e}"
                    st.session_state.progress_messages.append(
                        {"role": "assistant", "content": err}
                    )
                    st.error(err)


def main():
    sidebar_keys()
    _ensure_state()

    try:
        db_url = os.getenv("MEMORI_DB_URL", "") or None
        provider = os.getenv("_STUDY_PROVIDER", "openai")
        env_key = _PROVIDER_KEY_ENV.get(provider, "OPENAI_API_KEY")
        api_key = os.getenv(env_key, "")
        memori_mgr = get_memori_manager(provider, api_key, db_url)
    except Exception as e:
        st.error(
            f"Failed to initialize Memori. "
            f"Check your API key and DB settings. Details: {e}"
        )
        return

    # After Memori is ready, try to restore learner profile from Memori on fresh loads.
    # This lets the app remember your profile across refreshes and new runs.
    if st.session_state.learner_profile is None:
        profile_dict: dict | None = None
        try:
            profile_dict = memori_mgr.get_latest_learner_profile()
        except Exception:
            profile_dict = None

        if profile_dict:
            try:
                st.session_state.learner_profile = LearnerProfile(**profile_dict)
            except Exception:
                # Fall back to LLM-based reconstruction if structured load fails.
                _maybe_restore_profile_from_memori(memori_mgr)
        else:
            # No structured profile found – try to reconstruct via Memori + LLM.
            _maybe_restore_profile_from_memori(memori_mgr)

    tab1, tab2, tab3 = st.tabs(
        ["🧭 Study Plan", "📅 Today’s Session", "📈 Progress & Memory"]
    )

    with tab1:
        study_plan_tab(memori_mgr)
    with tab2:
        today_session_tab(memori_mgr)
    with tab3:
        progress_tab(memori_mgr)


if __name__ == "__main__":
    main()
