"""Memori integration for persistent memory."""

from pathlib import Path

from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class MemoryManager:
    """Manage Memori integration for persistent memory."""

    def __init__(
        self,
        llm_client,
        entity_id: str,
        process_id: str = "memori-contributor",
        db_path: str | None = None,
    ) -> None:
        """
        Initialize memory manager with Memori.

        Args:
            llm_client: The LLM client to register with Memori
            entity_id: Unique identifier for the user/entity
            process_id: Process identifier for this assistant
            db_path: Custom database path (optional)
        """
        if db_path is None:
            db_path = str(Path.home() / ".memori_contributor" / "memori.db")

        db_path_obj = Path(db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLAlchemy engine
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)

        # Register LLM client with Memori
        self.mem = Memori(conn=SessionLocal).llm.register(llm_client)
        self.mem.attribution(entity_id=entity_id, process_id=process_id)
        self.mem.config.storage.build()

    def wait(self) -> None:
        """Wait for async augmentation processing to complete."""
        self.mem.augmentation.wait()

    def get_facts(self) -> list[str]:
        """Get stored facts from memory."""
        try:
            # Query the database for facts
            from sqlalchemy import text

            engine = self.mem.config.conn()
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT content FROM memori_entity_fact LIMIT 10")
                )
                facts = [row[0] for row in result]
                return facts
        except Exception:
            return []

    def get_session_id(self) -> str:
        """Get current session ID."""
        return self.mem.config.session_id

    def new_session(self) -> None:
        """Start a new session."""
        self.mem.new_session()
