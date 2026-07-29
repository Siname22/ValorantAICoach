from agents.shared.container import container
from backend.app.services.player_service import PlayerService
from backend.providers.henrik.config import HenrikConfig
from backend.providers.henrik.provider import HenrikProvider
from backend.providers.riot.config import RiotConfig
from backend.providers.riot.provider import RiotProvider
from backend.providers.tracker.config import TrackerConfig
from backend.providers.tracker.provider import TrackerProvider


def get_player_service() -> PlayerService:
    """
    Dependency provider for FastAPI to get the PlayerService instance.
    Ensures all providers are registered in the container before resolution.
    """
    try:
        return container.resolve(PlayerService)
    except KeyError:
        # Register providers if not already present
        try:
            riot = container.resolve(RiotProvider)
        except KeyError:
            riot = RiotProvider(RiotConfig())
            container.register_provider("riot", riot)

        try:
            henrik = container.resolve(HenrikProvider)
        except KeyError:
            henrik = HenrikProvider(HenrikConfig())
            container.register_provider("henrik", henrik)

        try:
            tracker = container.resolve(TrackerProvider)
        except KeyError:
            tracker = TrackerProvider(TrackerConfig())
            container.register_provider("tracker", tracker)

        # Register and return PlayerService
        service = PlayerService(riot, henrik, tracker)
        container.register_instance(PlayerService, service)
        return service
