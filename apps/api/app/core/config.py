from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    web_app_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    database_url: str = "postgresql+asyncpg://dripjudge:dripjudge@localhost:5432/dripjudge"
    redis_url: str = "redis://localhost:6379/0"
    max_upload_mb: int = Field(default=8, ge=1, le=40)
    upload_storage_path: Path = Path(".uploads")
    clip_embedding_dimensions: int = 512

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("web_app_url", "api_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origins(self) -> list[str]:
        return [self.web_app_url, "http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
