from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from backend.providers.base.config import ProviderConfig, validate_http_url


class RiotConfig(ProviderConfig):
    """Official VALORANT shard and continental account routing.

    RIOT_REGION selects eu, na, latam, br, ap or kr and supplies the default
    shard host. RIOT_BASE_URL can override that host. RIOT_ACCOUNT_BASE_URL
    independently selects the nearest account cluster: europe (default),
    americas or asia, e.g. https://americas.api.riotgames.com for North America.
    """

    model_config = SettingsConfigDict(env_prefix="RIOT_")

    api_key: str | None = Field(None, description="API key for Riot Games API")
    base_url: str = Field(
        "https://eu.api.riotgames.com",
        description="VALORANT shard host, without an API path",
    )
    account_base_url: str = Field(
        "https://europe.api.riotgames.com",
        description="Continental account-v1 host (europe, americas or asia)",
    )
    region: Literal["eu", "na", "latam", "br", "ap", "kr"] = "eu"
    match_history_limit: int = Field(
        10, ge=1, le=20, description="Maximum match details fetched per history"
    )

    @field_validator("account_base_url")
    @classmethod
    def validate_account_url(cls, value: str) -> str:
        return validate_http_url(value)

    @model_validator(mode="after")
    def use_region_host(self) -> Self:
        if "base_url" not in self.model_fields_set:
            self.base_url = f"https://{self.region}.api.riotgames.com"
        return self
