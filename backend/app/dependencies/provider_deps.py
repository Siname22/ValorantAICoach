import logging

from backend.app.core.config import get_settings
from backend.app.services.player_service import PlayerService
from backend.app.storage.player_service import PersistentPlayerService
from backend.app.storage.repository import SQLPlayerStore
from backend.providers.henrik.config import HenrikConfig
from backend.providers.henrik.provider import HenrikProvider
from backend.providers.riot.config import RiotConfig
from backend.providers.riot.provider import RiotProvider
from backend.providers.tracker.config import TrackerConfig
from backend.providers.tracker.provider import TrackerProvider
from fastapi import Request
from pydantic import ValidationError
from pydantic_settings import SettingsError

logger = logging.getLogger(__name__)


def create_player_service() -> PlayerService:
    """Build the application service using only configured, enabled providers."""
    settings = get_settings()
    store = (
        SQLPlayerStore(
            settings.database_url,
            ttl_seconds=settings.database_cache_ttl_seconds,
            test_mode=settings.app_env == "test",
        )
        if settings.database_enabled
        else None
    )
    providers = {}
    disabled = {}
    for name, config_type, provider_type in (
        ("riot", RiotConfig, RiotProvider),
        ("henrik", HenrikConfig, HenrikProvider),
        ("tracker", TrackerConfig, TrackerProvider),
    ):
        try:
            config = config_type()
        except (ValidationError, SettingsError):
            disabled[name] = "misconfigured"
            logger.warning("Invalid %s provider configuration", name)
            continue
        if not config.enabled or not config.api_key or not config.api_key.strip():
            disabled[name] = "disabled"
            continue
        providers[f"{name}_provider"] = provider_type(config)
    if store is not None:
        return PersistentPlayerService(
            store=store, **providers, disabled_providers=disabled
        )
    return PlayerService(**providers, disabled_providers=disabled)


async def get_player_service(request: Request) -> PlayerService:
    """Resolve the shared service created by the application's lifespan."""
    return request.app.state.player_service
