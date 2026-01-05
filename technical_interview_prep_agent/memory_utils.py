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
    aligned with the project requirements for the Interview Prep agent.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        sqlite_path: str | None = None,
        entity_id: str = "interview-prep-user",
        process_id: str = "interview-prep",
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

        # Optional connectivity check + ensure our own helper table exists.
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

    # ---- High-level helpers for the Interview Prep demo ----

    def log_candidate_profile(self, profile_data: dict[str, Any]) -> None:
        """
        Store a structured candidate profile in Memori via a tagged JSON payload.

        The tag `INTERVIEW_PROFILE` is used so we can later search specifically
        for profile documents.
        """
        payload = {
            "type": "interview_profile",
            "version": 1,
            "profile": profile_data,
        }
        tagged_text = "INTERVIEW_PROFILE " + json.dumps(payload, ensure_ascii=False)

        # Send via the registered OpenAI client so Memori can capture it.
        self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Store the following technical interview candidate profile "
                        "document in long-term memory so it can be recalled later:\n\n"
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

    def log_problem_attempt(self, attempt_summary: str) -> None:
        """
        Store one coding interview problem attempt summary (metadata + code + evaluation).

        The summary should already embed useful signals about:
        - Problem difficulty and patterns.
        - Whether the attempt was successful.
        - Hints used, main bugs, and recommended follow-ups.
        """
        system_prompt = (
            "The following text describes one coding interview practice attempt for "
            "this candidate (problem metadata, their solution, hints, and evaluation). "
            "Extract and remember algorithm/data-structure patterns, difficulty level, "
            "common mistakes, and any signs of improvement or regression."
        )
        self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": attempt_summary,
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

    def summarize_performance(self, question: str) -> str:
        """
        Ask Memori/LLM to summarize the candidate's interview performance.

        Example questions:
        - "What algorithm patterns am I weakest at?"
        - "How have I improved over the last 10 attempts?"
        """
        system_prompt = (
            "You are an AI technical interview coach with long-term memory about the "
            "candidate's past coding interview practice attempts and profile. "
            "Answer the user's question using those memories. Focus on:\n"
            "- Weak and strong algorithm/data-structure patterns.\n"
            "- Difficulty bands (easy/medium/hard) they handle well or poorly.\n"
            "- Trends over time and specific, actionable next steps."
        )
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content or ""

    def set_free_uses_remaining(self, remaining: int) -> None:
        """
        Persist the remaining free-usage quota for the current entity/process
        in a small SQLite table (separate from Memori's own schema).
        """
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
        """
        Retrieve the remaining free-usage quota for the current entity/process
        from the local SQLite helper table.
        """
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
        """
        Attempt to retrieve the most recently stored candidate profile from Memori.

        Uses Memori's recall API, which respects the current attribution
        (entity_id / process_id / session) so profiles remain isolated per
        logical "user" in a multi-tenant app.
        """
        recall_fn = getattr(self.memori, "recall", None)
        if recall_fn is None:
            return None

        try:
            results: list[Any] = (
                recall_fn("INTERVIEW_PROFILE", limit=5) or []  # type: ignore[call-arg]
            )
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
            if obj.get("type") != "interview_profile":
                continue
            profile = obj.get("profile")
            if isinstance(profile, dict):
                return profile

        return None
