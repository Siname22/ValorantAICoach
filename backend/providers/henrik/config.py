from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.providers.base.config import ProviderConfig


class HenrikConfig(ProviderConfig):
    """Configuration for HenrikDev provider, inheriting from Base ProviderConfig."""

    model_config = SettingsConfigDict(env_prefix="HENRIK_")

    api_key: str | None = Field(None, description="API key for HenrikDev")
    base_url: str = Field(
        "https://api.henrikdev.xyz/valorant/v1",
        description="Base URL for HenrikDev API",
    )
    health_region: str = Field("eu", description="Region for the status endpoint")
