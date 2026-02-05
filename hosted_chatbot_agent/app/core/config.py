from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    These are loaded from environment variables or .env file.
    For Memori hosted, we only need:
    - OpenAI API key (for the LLM)
    - Memori API key (for hosted memory service)
    """

    # API Keys
    openai_api_key: str
    memori_api_key: str

    # LLM Configuration
    openai_model: str = "gpt-4o-mini"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS Settings (for frontend integration)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Application Metadata
    app_name: str = "Memori Hosted Chatbot Demo"
    app_version: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    """
    return Settings()
