import httpx
from pydantic import Field, HttpUrl, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_http_url(value: str) -> str:
    """Validate HTTP URLs without normalizing provider-specific path prefixes."""
    if value != value.strip():
        raise ValueError("Provider URL cannot contain surrounding whitespace")
    TypeAdapter(HttpUrl).validate_python(value)
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise ValueError("Invalid provider URL") from error
    if url.scheme not in ("http", "https") or not url.host:
        raise ValueError("Provider URL requires an HTTP scheme and a host")
    return value


class ProviderConfig(BaseSettings):
    """Base configuration for any provider, utilizing Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(True, description="Whether the provider is enabled")
    base_url: str = Field(..., description="Base URL for the provider API")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(30.0, gt=0, description="Request timeout in seconds")
    retries: int = Field(3, ge=0, description="Number of retries for failed requests")
    backoff_factor: float = Field(
        0.5, ge=0, description="Factor for exponential backoff"
    )
    default_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Default headers for all requests",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return validate_http_url(value)
