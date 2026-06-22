import logging

from anthropic import Anthropic, AnthropicBedrock
from memori import Memori
from openai import OpenAI

from core.config import get_settings
from core.git_context import get_context_id

logger = logging.getLogger(__name__)


class BaseAgent:
    NAME = "Agent"
    PROCESS_ID = "memori-mesh"
    SYSTEM_PROMPT = "You are a helpful AI assistant."

    def __init__(self, repo_path: str = "."):
        settings = get_settings()
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.repo_path = repo_path
        self.last_prompt_tokens: int = 0
        self._client, self.mem = self._init_client(settings)

    @staticmethod
    def _build_conn(settings):
        """Return a conn factory for the selected database backend, or None for Memori Cloud."""
        backend = settings.db_backend.lower()

        if backend == "cloud":
            return None

        if backend == "sqlite":
            import sqlite3
            path = settings.db_path or "memori.db"
            return lambda: sqlite3.connect(path)

        if backend == "mongodb":
            from pymongo import MongoClient
            uri = settings.db_connection_string or "mongodb://localhost:27017"
            mongo = MongoClient(uri)
            try:
                db = mongo.get_default_database()
            except Exception:
                db = mongo["memori"]
            return lambda: db

        if backend == "oceanbase":
            try:
                from sqlalchemy.dialects import registry
                registry.register("mysql.oceanbase", "pyobvector.schema.dialect", "OceanBaseDialect")
            except Exception:
                pass

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        dsn = settings.db_connection_string
        if not dsn:
            raise ValueError(f"DB_CONNECTION_STRING is required for backend '{backend}'")
        engine = create_engine(dsn, pool_pre_ping=True)
        return sessionmaker(bind=engine)

    def _init_client(self, settings):
        conn = self._build_conn(settings)
        mem = Memori(conn=conn) if conn is not None else Memori()

        if self.provider in ("openai", "gemini"):
            kwargs: dict = {"api_key": settings.effective_openai_key}
            if settings.effective_base_url:
                kwargs["base_url"] = settings.effective_base_url
            client = OpenAI(**kwargs)
            registered = mem.llm.register(client)
            return client, registered

        if self.provider == "anthropic":
            client = Anthropic(api_key=settings.anthropic_api_key)
            registered = mem.llm.register(client)
            return client, registered

        if self.provider == "bedrock":
            client = AnthropicBedrock(
                aws_access_key=settings.aws_access_key_id,
                aws_secret_key=settings.aws_secret_access_key,
                aws_region=settings.aws_region,
            )
            registered = mem.llm.register(client)
            return client, registered

        raise ValueError(f"Unknown provider: {self.provider}")

    def _set_context(self) -> str:
        context_id = get_context_id(self.repo_path)
        self.mem.attribution(entity_id=context_id, process_id=self.PROCESS_ID)
        return context_id

    def run(self, task: str, prior_context: str = "") -> str:
        context_id = self._set_context()
        logger.debug("%s running | context=%s | provider=%s", self.NAME, context_id, self.provider)

        user_message = task
        if prior_context:
            user_message = f"Prior agent output:\n{prior_context}\n\nYour task:\n{task}"

        if self.provider in ("openai", "gemini"):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1000,
            )
            if response.usage:
                self.last_prompt_tokens = response.usage.prompt_tokens
            return response.choices[0].message.content or ""

        # Anthropic + Bedrock share the messages API
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        self.last_prompt_tokens = response.usage.input_tokens
        return response.content[0].text  # type: ignore[union-attr]
