import json
import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Lazy imports to reduce memory at startup
if TYPE_CHECKING:
    pass


class MemoriManager:
    """
    Thin wrapper around Memori + LLM client + SQLite (via SQLAlchemy).

    Supports OpenAI, Gemini (via OpenAI-compatible endpoint), and Claude.
    Set provider via the `provider` argument or LLM_PROVIDER env var.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        sqlite_path: str | None = None,
        entity_id: str = "wellness-user",
        process_id: str = "wellness-coach",
        provider: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from memori import Memori

        # Resolve provider
        self._provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()

        # Resolve API key (api_key > openai_api_key > env)
        _api_key = api_key or openai_api_key
        if not _api_key:
            if self._provider == "gemini":
                _api_key = os.getenv("GEMINI_API_KEY", "")
            elif self._provider == "claude":
                _api_key = os.getenv("ANTHROPIC_API_KEY", "")
            else:
                _api_key = os.getenv("OPENAI_API_KEY", "")
        if not _api_key:
            raise RuntimeError(
                f"No API key for provider '{self._provider}'. "
                "Set OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY."
            )

        # Resolve SQLite path (env override allowed)
        db_path = (
            sqlite_path
            or os.getenv("WELLNESS_SQLITE_PATH")
            or os.getenv("SQLITE_DB_PATH")
            or "./memori_wellness.sqlite"
        )
        database_url = f"sqlite:///{db_path}"

        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
        )

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS wellness_free_usage (
                        entity_id TEXT PRIMARY KEY,
                        remaining INTEGER NOT NULL
                    )
                    """
                )
            )

        self.SessionLocal: sessionmaker = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

        # Initialize provider-specific client + register with Memori
        if self._provider == "claude":
            from anthropic import Anthropic

            claude_client = Anthropic(api_key=_api_key)
            mem = Memori(conn=self.SessionLocal).anthropic.register(claude_client)
            self._claude_client = claude_client
            self._openai_client = None
        else:
            from openai import OpenAI

            if self._provider == "gemini":
                openai_client = OpenAI(api_key=_api_key, base_url=GEMINI_BASE_URL)
            else:
                openai_client = OpenAI(api_key=_api_key)
            mem = Memori(conn=self.SessionLocal).openai.register(openai_client)
            self._openai_client = openai_client
            self._claude_client = None

        mem.attribution(entity_id=entity_id, process_id=process_id)
        if mem.config.storage is not None:
            mem.config.storage.build()

        self.memori: Memori = mem
        # Backward compat alias
        self.openai_client = self._openai_client
        self.sqlite_path = db_path
        self.entity_id = entity_id

    def _default_model(self) -> str:
        if self._provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        if self._provider == "claude":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        return os.getenv("WELLNESS_MODEL", "gpt-4o-mini")

    def _chat(self, system: str, user: str) -> str:
        """Unified LLM completion across OpenAI, Gemini, and Claude."""
        model = self._default_model()
        if self._provider == "claude":
            assert self._claude_client is not None
            response = self._claude_client.messages.create(
                model=model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        assert self._openai_client is not None
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        response = self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def get_db(self) -> Session:
        return self.SessionLocal()

    def log_wellness_profile(self, profile_data: dict[str, Any]) -> None:
        """Store a structured wellness profile in Memori."""
        payload = {
            "type": "wellness_profile",
            "version": 1,
            "profile": profile_data,
        }
        tagged_text = "WELLNESS_PROFILE " + json.dumps(payload, ensure_ascii=False)
        self._chat(
            system="",
            user=(
                "Store the following wellness profile document in long-term memory "
                "so it can be recalled later:\n\n"
                f"{tagged_text}"
            ),
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def log_daily_habit(self, habit_summary: str) -> None:
        """Store one daily habit log entry (sleep, exercise, nutrition, mood)."""
        self._chat(
            system=(
                "The following text describes one day's wellness habit log for "
                "this user (sleep, exercise, nutrition, mood metrics). "
                "Extract and remember patterns, correlations, and trends that can "
                "help identify what works best for this user's wellness journey."
            ),
            user=habit_summary,
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def summarize_wellness_performance(self, question: str) -> str:
        """Ask Memori/LLM to summarize the user's wellness performance."""
        return self._chat(
            system=(
                "You are an AI wellness coach with long-term memory about the "
                "user's past wellness habit logs and profile. "
                "Answer the user's question using those memories. Focus on:\n"
                "- Patterns in sleep, exercise, nutrition, and mood.\n"
                "- Correlations between different wellness metrics.\n"
                "- Trends over time and specific, actionable recommendations."
            ),
            user=question,
        )

    def get_latest_wellness_profile(self) -> dict[str, Any] | None:
        """Retrieve the most recently stored wellness profile from Memori."""
        recall_fn = getattr(self.memori, "recall", None)
        if recall_fn is None:
            return None

        try:
            results: list[Any] = recall_fn("WELLNESS_PROFILE", limit=5) or []
        except Exception:
            return None

        for r in results:
            if isinstance(r, dict):
                text = str(r.get("content") or "")
            else:
                text = str(r)

            idx = text.find("{")
            jdx = text.rfind("}")
            if idx == -1 or jdx == -1:
                continue
            try:
                obj = json.loads(text[idx : jdx + 1])
            except Exception:
                continue

            if not isinstance(obj, dict):
                continue
            if obj.get("type") != "wellness_profile":
                continue
            profile = obj.get("profile")
            if isinstance(profile, dict):
                return profile

        return None

    def identify_weaknesses(self) -> str:
        """Query Memori to identify wellness weaknesses and opportunities."""
        question = (
            "In 3–5 bullet points, summarize my weakest wellness areas and "
            "opportunities for improvement based on my habit history."
        )
        return self.summarize_wellness_performance(question)
