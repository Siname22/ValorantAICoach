from pydantic import Field

from backend.providers.base.config import ProviderConfig


class HenrikConfig(ProviderConfig):
    """Configuration for HenrikDev provider, inheriting from Base ProviderConfig."""

    api_key: str = Field(..., env="HENRIK_API_KEY", description="API key for HenrikDev")
    base_url: str = Field(
        "https://api.henrikdev.xyz/valorant/v1",
        env="HENRIK_BASE_URL",
        description="Base URL for HenrikDev API",
    )

    class Config:
        env_prefix = "HENRIK_"
        env_file = ".env"
        extra = "ignore"
