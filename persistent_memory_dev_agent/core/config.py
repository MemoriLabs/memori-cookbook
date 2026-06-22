from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class Settings(BaseSettings):
    # LLM provider selector: openai | gemini | anthropic | bedrock
    llm_provider: str = "gemini"

    # OpenAI / Gemini
    openai_api_key: str = ""
    google_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    # Anthropic
    anthropic_api_key: str = ""

    # AWS Bedrock
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # Memori
    memori_api_key: str = ""

    # Memory storage backend: cloud | sqlite | postgresql | mysql | mariadb |
    #                          mongodb | cockroachdb | tidb | oceanbase | oracle
    db_backend: str = "cloud"
    db_connection_string: str = ""  # DSN for all SQL + MongoDB backends
    db_path: str = "memori.db"      # SQLite file path

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def effective_openai_key(self) -> str:
        return self.google_api_key or self.openai_api_key

    @property
    def effective_base_url(self) -> str | None:
        return GEMINI_BASE_URL if self.llm_provider == "gemini" else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
