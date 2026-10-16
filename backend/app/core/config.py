import logging
import os
import secrets
import sys
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

MIN_JWT_SECRET_LENGTH = 32
INSECURE_ALLOWED_ENVS = frozenset({"development", "dev", "local", "test"})


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
    database_auto_sync_interval_seconds: int = Field(
        default=0,
        ge=0,
        le=86400,
        description=(
            "Interval for periodic scheduled coaching sync of tracked accounts "
            "(0 to disable)"
        ),
    )
    jwt_secret_key: str | None = Field(
        default=None,
        description=(
            "HS256 signing secret. Mandatory (>= 32 chars) outside development "
            "and test; startup aborts if missing."
        ),
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=1440, ge=1, le=525600)
    admin_emails: str = Field(
        default="",
        description="Comma-separated e-mails granted the admin role.",
    )
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:3000",
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    )
    enable_security_headers: bool = True
    enable_hsts: bool = False
    max_request_body_size_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = Field(default=120, ge=1)
    rate_limit_burst: int = Field(default=30, ge=1)
    rate_limit_trusted_proxies: str = Field(
        default="127.0.0.1,::1,testclient",
        description=(
            "Comma-separated IPs or hostnames of trusted reverse proxies "
            "allowed to forward client IPs via X-Forwarded-For."
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def admin_email_set(self) -> frozenset[str]:
        return frozenset(
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        )

    @property
    def trusted_proxy_set(self) -> frozenset[str]:
        return frozenset(
            ip.strip().lower()
            for ip in self.rate_limit_trusted_proxies.split(",")
            if ip.strip()
        )

    @model_validator(mode="after")
    def _require_jwt_secret(self) -> "Settings":
        is_test_runner = (
            self.app_env.lower() in ("test", "testing")
            or "PYTEST_CURRENT_TEST" in os.environ
            or "pytest" in sys.modules
        )
        if is_test_runner and "RATE_LIMIT_ENABLED" not in os.environ:
            self.rate_limit_enabled = False
        secret = (self.jwt_secret_key or "").strip()
        if len(secret) >= MIN_JWT_SECRET_LENGTH:
            return self
        if self.app_env.lower() in INSECURE_ALLOWED_ENVS:
            if secret:
                logger.warning("JWT_SECRET_KEY is shorter than recommended.")
                return self
            logger.warning(
                "JWT_SECRET_KEY is not set; using an ephemeral random secret. "
                "Issued tokens become invalid when the process restarts."
            )
            self.jwt_secret_key = secrets.token_urlsafe(48)
            return self
        raise ValueError(
            f"JWT_SECRET_KEY must be set to at least {MIN_JWT_SECRET_LENGTH} "
            f"characters when APP_ENV={self.app_env!r}."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
