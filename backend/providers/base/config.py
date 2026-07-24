from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    timeout: float = Field(30.0, description="Request timeout in seconds")
    retries: int = Field(3, description="Number of retries for failed requests")
    backoff_factor: float = Field(0.5, description="Factor for exponential backoff")
    default_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Default headers for all requests",
    )
