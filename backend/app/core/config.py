from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "convhub-api"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/convhub",
        description="Async SQLAlchemy database URL (postgresql+asyncpg://...)",
    )

    cors_origins: str = "http://localhost:3000"

    jwt_secret_key: str = Field(
        default="dev-only-change-me-in-production-use-32-chars-min",
        min_length=32,
        description="Secret key for signing JWT access tokens",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    ai_provider: Literal["mock", "anthropic", "ollama", "openai", "gemini", "groq"] = "mock"
    ai_model: str = "claude-sonnet-4-20250514"
    ai_system_prompt: str = "You are a helpful assistant."
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    anthropic_api_key: str | None = Field(
        default=None,
        description="Development-only fallback when no workspace AI account is configured",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="Development-only fallback for OpenAI when no workspace AI account is configured",
    )
    openai_model: str = "gpt-4o"
    gemini_api_key: str | None = Field(
        default=None,
        description="Development-only fallback for Gemini when no workspace AI account is configured",
    )
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str | None = Field(
        default=None,
        description="Development-only fallback for Groq when no workspace AI account is configured",
    )
    groq_model: str = "llama-3.3-70b-versatile"
    credentials_encryption_key: str = Field(
        default="lHOGnkjdkIA2CqtPkQKagGz7u7JIwHBDO5x0V3Z2yjY=",
        description="Fernet key for encrypting workspace AI account credentials",
    )

    enable_demo_mode: bool = Field(
        default=False,
        description="Expose demo administration endpoints and testing toolkit",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
