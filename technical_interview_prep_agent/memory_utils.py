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
        entity_id: str = "interview-prep-user",
        process_id: str = "interview-prep",
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
            or os.getenv("INTERVIEW_SQLITE_PATH")
            or os.getenv("SQLITE_DB_PATH")
            or "./memori_interview.sqlite"
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
                    CREATE TABLE IF NOT EXISTS interview_free_usage (
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
        return os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")

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

    def log_candidate_profile(self, profile_data: dict[str, Any]) -> None:
        """Store a structured candidate profile in Memori."""
        payload = {
            "type": "interview_profile",
            "version": 1,
            "profile": profile_data,
        }
        tagged_text = "INTERVIEW_PROFILE " + json.dumps(payload, ensure_ascii=False)
        self._chat(
            system="",
            user=(
                "Store the following technical interview candidate profile "
                "document in long-term memory so it can be recalled later:\n\n"
                f"{tagged_text}"
            ),
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def log_problem_attempt(self, attempt_summary: str) -> None:
        """Store one coding interview problem attempt summary."""
        self._chat(
            system=(
                "The following text describes one coding interview practice attempt for "
                "this candidate (problem metadata, their solution, hints, and evaluation). "
                "Extract and remember algorithm/data-structure patterns, difficulty level, "
                "common mistakes, and any signs of improvement or regression."
            ),
            user=attempt_summary,
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def summarize_performance(self, question: str) -> str:
        """Ask Memori/LLM to summarize the candidate's interview performance."""
        return self._chat(
            system=(
                "You are an AI technical interview coach with long-term memory about the "
                "candidate's past coding interview practice attempts and profile. "
                "Answer the user's question using those memories. Focus on:\n"
                "- Weak and strong algorithm/data-structure patterns.\n"
                "- Difficulty bands (easy/medium/hard) they handle well or poorly.\n"
                "- Trends over time and specific, actionable next steps."
            ),
            user=question,
        )

    def set_free_uses_remaining(self, remaining: int) -> None:
        """Persist the remaining free-usage quota for the current entity."""
        if not getattr(self, "entity_id", None):
            return

        with self.get_db() as db:
            db.execute(
                text(
                    """
                    INSERT INTO interview_free_usage (entity_id, remaining)
                    VALUES (:entity_id, :remaining)
                    ON CONFLICT(entity_id) DO UPDATE SET remaining = :remaining
                    """
                ),
                {"entity_id": self.entity_id, "remaining": int(remaining)},
            )
            db.commit()

    def get_free_uses_remaining(self, default_total: int = 6) -> int:
        """Retrieve the remaining free-usage quota for the current entity."""
        if not getattr(self, "entity_id", None):
            return default_total

        with self.get_db() as db:
            row = db.execute(
                text(
                    "SELECT remaining FROM interview_free_usage WHERE entity_id = :entity_id"
                ),
                {"entity_id": self.entity_id},
            ).fetchone()

        if row is None:
            return default_total

        try:
            return int(row[0])
        except (TypeError, ValueError):
            return default_total

    def get_latest_candidate_profile(self) -> dict[str, Any] | None:
        """Retrieve the most recently stored candidate profile from Memori."""
        recall_fn = getattr(self.memori, "recall", None)
        if recall_fn is None:
            return None

        try:
            results: list[Any] = recall_fn("INTERVIEW_PROFILE", limit=5) or []
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
            if obj.get("type") != "interview_profile":
                continue
            profile = obj.get("profile")
            if isinstance(profile, dict):
                return profile

        return None
