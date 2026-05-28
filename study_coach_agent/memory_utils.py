import json
import os
from typing import Any, cast

from dotenv import load_dotenv
from memori import Memori
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover - optional dependency
    MongoClient = None


load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class MemoriManager:
    """
    Thin wrapper around Memori + LLM client + SQLAlchemy engine.

    Supports OpenAI, Gemini (via OpenAI-compatible endpoint), and Claude.
    Also supports MongoDB URLs.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        db_url: str | None = None,
        sqlite_path: str = "./memori_study.sqlite",
        entity_id: str = "study-coach-user",
        process_id: str = "study-coach",
        provider: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.sqlite_path = sqlite_path
        self.entity_id = entity_id
        self.process_id = process_id
        self.db_url = db_url or ""

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

        self.SessionLocal: sessionmaker | None = None

        # Decide connection strategy based on db_url scheme
        conn_arg: Any
        db_url_effective = self.db_url.strip()

        if db_url_effective.startswith("mongodb://") or db_url_effective.startswith(
            "mongodb+srv://"
        ):
            if MongoClient is None:
                raise RuntimeError(
                    "pymongo is required for MongoDB connections. "
                    "Install it or use a SQLAlchemy database URL."
                )
            mongo_client = MongoClient(db_url_effective)

            from urllib.parse import urlparse

            parsed = urlparse(db_url_effective)
            db_name = parsed.path.lstrip("/") or "memori"

            def get_db():
                return mongo_client[db_name]

            conn_arg = get_db
        else:
            if db_url_effective:
                database_url = db_url_effective
            else:
                database_url = f"sqlite:///{self.sqlite_path}"

            engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
            if database_url.startswith("sqlite"):
                engine_kwargs["connect_args"] = {"check_same_thread": False}

            engine = create_engine(database_url, **engine_kwargs)

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
            conn_arg = self.SessionLocal

        # Initialize provider-specific client + register with Memori
        if self._provider == "claude":
            from anthropic import Anthropic

            claude_client = Anthropic(api_key=_api_key)
            mem = Memori(conn=conn_arg).anthropic.register(claude_client)
            self._claude_client = claude_client
            self._openai_client = None
        else:
            from openai import OpenAI

            if self._provider == "gemini":
                openai_client = OpenAI(api_key=_api_key, base_url=GEMINI_BASE_URL)
            else:
                openai_client = OpenAI(api_key=_api_key)
            mem = Memori(conn=conn_arg).openai.register(openai_client)
            self._openai_client = openai_client
            self._claude_client = None

        mem.attribution(entity_id=self.entity_id, process_id=self.process_id)
        if mem.config.storage is not None:
            mem.config.storage.build()

        self.memori: Memori = mem
        # Backward compat alias
        self.openai_client = self._openai_client

    def _default_model(self) -> str:
        if self._provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        if self._provider == "claude":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        return os.getenv("STUDY_MODEL", "gpt-4o-mini")

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
            return response.content[0].text  # type: ignore
        assert self._openai_client is not None
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        response = self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        content = cast(str | None, response.choices[0].message.content)
        return content or ""

    def get_db(self) -> Session | None:
        if self.SessionLocal is None:
            return None
        return self.SessionLocal()

    def log_learner_profile(self, profile_data: dict[str, Any]) -> None:
        """Store a structured learner profile in Memori."""
        payload = {
            "type": "study_profile",
            "version": 1,
            "profile": profile_data,
        }
        tagged_text = "STUDY_COACH_PROFILE " + json.dumps(payload, ensure_ascii=False)
        self._chat(
            system="",
            user=(
                "Store the following study coach learner profile document "
                "in long-term memory so it can be recalled later:\n\n"
                f"{tagged_text}"
            ),
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def log_study_session(self, session_summary: str) -> None:
        """Store a single study session summary."""
        prompt = (
            "The following text summarizes one study session for this learner. "
            "Extract and remember: topic, difficulty, performance, misconceptions, "
            "and any motivation signals:\n\n"
            f"{session_summary}"
        )
        self._chat(
            system=prompt,
            user="Confirm that you have updated the learner's memory.",
        )

        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def summarize_progress(self, question: str) -> str:
        """Ask Memori/LLM to summarize progress, weak/strong topics, or patterns."""
        return self._chat(
            system=(
                "You are an AI study coach with long-term memory about the learner's "
                "past study sessions, topics, scores, and motivation. Answer the user's "
                "question using those memories. Be concrete about weak/strong topics "
                "and any patterns across time (time of day, resource type, etc.)."
            ),
            user=question,
        )

    def get_latest_learner_profile(self) -> dict[str, Any] | None:
        """Retrieve the most recently stored learner profile from Memori."""
        search_fn = getattr(self.memori, "search", None)
        if search_fn is None:
            return None

        try:
            results: list[Any] = search_fn("STUDY_COACH_PROFILE", limit=5) or []
        except Exception:
            return None

        for r in results:
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
            if obj.get("type") != "study_profile":
                continue
            profile = obj.get("profile")
            if isinstance(profile, dict):
                return profile

        return None
