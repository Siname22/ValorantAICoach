from pydantic import Field

from backend.providers.base.config import ProviderConfig


class RiotConfig(ProviderConfig):
    """Configuration for Riot API provider, inheriting from Base ProviderConfig."""

    api_key: str = Field(
        ..., env="RIOT_API_KEY", description="API key for Riot Games API"
    )
    base_url: str = Field(
        "https://americas.api.riotgames.com/valorant/v1",
        env="RIOT_BASE_URL",
        description="Base URL for Riot Games API (e.g., americas.api.riotgames.com)",
    )
    region: str = Field(
        "na",
        env="RIOT_REGION",
        description="Default region for Riot API requests (e.g., na, eu, ap)",
    )

    class Config:
        env_prefix = "RIOT_"
        env_file = ".env"
        extra = "ignore"
