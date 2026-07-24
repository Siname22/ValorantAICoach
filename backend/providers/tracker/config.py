from pydantic_settings import SettingsConfigDict

from backend.providers.base.config import ProviderConfig


class TrackerConfig(ProviderConfig):

    model_config = SettingsConfigDict(
        env_prefix="TRACKER_",
        env_file=".env",
        extra="ignore",
    )

    api_key: str

    base_url: str = "https://public-api.tracker.gg/v2/valorant/standard"
