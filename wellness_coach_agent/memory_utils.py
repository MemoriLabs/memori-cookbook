import json
import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

# Lazy imports to reduce memory at startup
if TYPE_CHECKING:
    pass


class MemoriManager:
    """
    Thin wrapper around Memori + OpenAI client + SQLite (via SQLAlchemy).

    This version is intentionally SQLite-only to keep deployment simple and
    aligned with the project requirements for the Wellness Coach agent.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        sqlite_path: str | None = None,
        entity_id: str = "wellness-user",
        process_id: str = "wellness-coach",
    ) -> None:
        # Lazy import heavy dependencies to reduce memory at startup
        from memori import Memori
        from openai import OpenAI

        # Resolve OpenAI key
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY is not set – cannot initialize Memori.")

        # Resolve SQLite path (env override allowed, but backend is always SQLite)
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

        # Optional connectivity check + ensure our own helper table exists.
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

        client = OpenAI(api_key=openai_key)
        mem = Memori(conn=self.SessionLocal).openai.register(client)
        mem.attribution(entity_id=entity_id, process_id=process_id)
        mem.config.storage.build()

        self.memori: Memori = mem
        self.openai_client: OpenAI = client
        self.sqlite_path = db_path
        self.entity_id = entity_id

    def get_db(self) -> Session:
        return self.SessionLocal()

    # ---- High-level helpers for the Wellness Coach demo ----

    def log_wellness_profile(self, profile_data: dict[str, Any]) -> None:
        """
        Store a structured wellness profile in Memori via a tagged JSON payload.

        The tag `WELLNESS_PROFILE` is used so we can later search specifically
        for profile documents.
        """
        payload = {
            "type": "wellness_profile",
            "version": 1,
            "profile": profile_data,
        }
        tagged_text = "WELLNESS_PROFILE " + json.dumps(payload, ensure_ascii=False)

        # Send via the registered OpenAI client so Memori can capture it.
        self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Store the following wellness profile document in long-term memory "
                        "so it can be recalled later:\n\n"
                        f"{tagged_text}"
                    ),
                },
            ],
        )

        # Best-effort explicit commit
        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            # Non-fatal; Memori should still persist in most configurations.
            pass

    def log_daily_habit(self, habit_summary: str) -> None:
        """
        Store one daily habit log entry (sleep, exercise, nutrition, mood).

        The summary should embed useful signals about:
        - Daily metrics and patterns
        - Correlations between different habits
        - Trends over time
        """
        system_prompt = (
            "The following text describes one day's wellness habit log for "
            "this user (sleep, exercise, nutrition, mood metrics). "
            "Extract and remember patterns, correlations, and trends that can "
            "help identify what works best for this user's wellness journey."
        )
        self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": habit_summary,
                },
            ],
        )

        # Best-effort explicit commit
        try:
            adapter = getattr(self.memori.config.storage, "adapter", None)
            if adapter is not None and hasattr(adapter, "commit"):
                adapter.commit()
        except Exception:
            pass

    def summarize_wellness_performance(self, question: str) -> str:
        """
        Ask Memori/LLM to summarize the user's wellness performance.

        Example questions:
        - "What are my weakest wellness areas?"
        - "How has my sleep improved over the last month?"
        - "What correlations exist between my habits?"
        """
        system_prompt = (
            "You are an AI wellness coach with long-term memory about the "
            "user's past wellness habit logs and profile. "
            "Answer the user's question using those memories. Focus on:\n"
            "- Patterns in sleep, exercise, nutrition, and mood.\n"
            "- Correlations between different wellness metrics.\n"
            "- Trends over time and specific, actionable recommendations."
        )
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content or ""

    def get_latest_wellness_profile(self) -> dict[str, Any] | None:
        """
        Attempt to retrieve the most recently stored wellness profile from Memori.

        Uses Memori's recall API, which respects the current attribution
        (entity_id / process_id / session) so profiles remain isolated per
        logical "user" in a multi-tenant app.
        """
        recall_fn = getattr(self.memori, "recall", None)
        if recall_fn is None:
            return None

        try:
            results: list[Any] = recall_fn("WELLNESS_PROFILE", limit=5) or []
        except Exception:
            return None

        for r in results:
            # mem.recall typically returns dicts with a 'content' field
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
        """
        Query Memori to identify wellness weaknesses and opportunities.
        """
        question = (
            "In 3–5 bullet points, summarize my weakest wellness areas and "
            "opportunities for improvement based on my habit history."
        )
        return self.summarize_wellness_performance(question)
