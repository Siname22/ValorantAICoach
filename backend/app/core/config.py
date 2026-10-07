from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ValorantAICoach"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = (
        "postgresql+psycopg://valorant:valorant@localhost:5432/valorant_ai_coach"
    )
    database_enabled: bool = False
    database_cache_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    database_auto_prune_interval_seconds: int = Field(
        default=0,
        ge=0,
        le=86400,
        description="Interval for periodic background cache pruning (0 to disable)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
