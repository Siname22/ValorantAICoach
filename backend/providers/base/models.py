from datetime import datetime
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, Field


class ProviderStatus(StrEnum):
    """Enumeration of possible provider statuses."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ProviderHealth(BaseModel):
    """Model for reporting provider health status."""

    status: ProviderStatus
    message: str = ""
    latency_ms: float | None = None
    last_check: datetime = Field(default_factory=datetime.now)


class RateLimit(BaseModel):
    """Model for tracking provider rate limit information."""

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None


class RequestMetadata(BaseModel):
    """Metadata for a provider request."""

    provider_name: str
    method: str
    endpoint: str
    status_code: int | None = None
    duration_ms: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


T = TypeVar("T")


class ProviderResponse[T](BaseModel):
    """Generic wrapper for provider responses."""

    data: T | None = None
    metadata: RequestMetadata
    rate_limit: RateLimit | None = None
    error: str | None = None
