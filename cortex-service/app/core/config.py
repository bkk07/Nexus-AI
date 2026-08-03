"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Cortex Service"
    app_env: str = "development"
    openai_api_key: str | None = Field(default=None, repr=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""

    return Settings()

