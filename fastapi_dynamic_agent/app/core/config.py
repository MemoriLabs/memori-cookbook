from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    memori_api_key: str

    openai_model: str = "gpt-4o-mini"

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    app_name: str = "Memori Hosted Chatbot Demo"
    app_version: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    # Pydantic's BaseSettings loads from environment variables automatically
    return Settings()  # type: ignore[call-arg]
