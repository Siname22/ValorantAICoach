from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.services.player_service import (
    PlayerNotFoundError,
    PlayerService,
)
from backend.providers.base.exceptions import NotFoundError, ServerError
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.henrik.models import (
    HenrikPlayer,
)
from backend.providers.riot.models import Player as RiotPlayer
from backend.providers.riot.models import Rank as RiotRank
from backend.providers.tracker.models import LifetimeStats as TrackerStats
from backend.providers.tracker.models import MatchSummary as TrackerMatch
from backend.providers.tracker.models import Player as TrackerPlayerModel
from backend.providers.tracker.models import PlayerIdentity as TrackerIdentity
from backend.providers.tracker.models import Rank as TrackerRank
from backend.providers.tracker.models import StatValue


@pytest.fixture
def mock_riot():
    provider = MagicMock()
    provider.name = "riot"
    provider.get_player_by_riot_id = AsyncMock()
    provider.get_player_match_history = AsyncMock()
    provider.get_player_rank = AsyncMock()
    provider.health_check = AsyncMock()
    return provider


@pytest.fixture
def mock_henrik():
    provider = MagicMock()
    provider.name = "henrik"
    provider.get_account = AsyncMock()
    provider.get_matches = AsyncMock()
    provider.health_check = AsyncMock()
    return provider


@pytest.fixture
def mock_tracker():
    provider = MagicMock()
    provider.name = "tracker"
    provider.get_player_profile = AsyncMock()
    provider.get_lifetime_stats = AsyncMock()
    provider.get_recent_matches = AsyncMock()
    provider.health_check = AsyncMock()
    return provider


@pytest.fixture
def player_service(mock_riot, mock_henrik, mock_tracker):
    return PlayerService(mock_riot, mock_henrik, mock_tracker)


@pytest.mark.asyncio
async def test_get_player_tracker_success(player_service, mock_tracker):
    # Setup Tracker success
    mock_tracker_identity = TrackerIdentity(
        platformId="riot",
        platformUserHandle="Test#NA1",
        platformUserIdentifier="t-123",
        avatarUrl="http://avatar.url",
    )
    mock_tracker.get_player_profile.return_value = TrackerPlayerModel(
        identity=mock_tracker_identity
    )
    mock_tracker.get_lifetime_stats.return_value = TrackerStats(
        kills=StatValue(value=10, displayValue="10"),
        deaths=StatValue(value=5, displayValue="5"),
        assists=StatValue(value=2, displayValue="2"),
        kdRatio=StatValue(value=2.0, displayValue="2.0"),
        headshotPct=StatValue(value=20.0, displayValue="20%"),
        winPct=StatValue(value=50.0, displayValue="50%"),
        rank=TrackerRank(tier_name="Diamond 1", icon_url="http://rank.icon"),
    )

    profile = await player_service.get_player("Test", "NA1")

    assert profile.game_name == "Test"
    assert profile.avatar_url == "http://avatar.url"
    assert profile.rank_name == "Diamond 1"
    mock_tracker.get_player_profile.assert_called_once()


@pytest.mark.asyncio
async def test_get_player_fallback_to_henrik(player_service, mock_tracker, mock_henrik):
    # Tracker fails, Henrik succeeds
    mock_tracker.get_player_profile.side_effect = ServerError("Tracker Down")
    mock_henrik.get_account.return_value = HenrikPlayer(
        puuid="h-123", name="Test", tag="NA1", region="na", account_level=100
    )

    profile = await player_service.get_player("Test", "NA1")

    assert profile.puuid == "h-123"
    assert profile.region == "na"
    mock_tracker.get_player_profile.assert_called_once()
    mock_henrik.get_account.assert_called_once()


@pytest.mark.asyncio
async def test_get_player_fallback_to_riot(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    # Tracker and Henrik fail, Riot succeeds
    mock_tracker.get_player_profile.side_effect = NotFoundError("Not in Tracker")
    mock_henrik.get_account.side_effect = ServerError("Henrik Down")
    mock_riot.get_player_by_riot_id.return_value = RiotPlayer(
        puuid="r-123", gameName="Test", tagLine="NA1", region="latam", accountLevel=50
    )

    profile = await player_service.get_player("Test", "NA1")

    assert profile.puuid == "r-123"
    assert profile.region == "latam"
    mock_riot.get_player_by_riot_id.assert_called_once()


@pytest.mark.asyncio
async def test_get_player_not_found_anywhere(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    mock_tracker.get_player_profile.side_effect = NotFoundError("No")
    mock_henrik.get_account.side_effect = NotFoundError("No")
    mock_riot.get_player_by_riot_id.side_effect = NotFoundError("No")

    with pytest.raises(PlayerNotFoundError):
        await player_service.get_player("Unknown", "000")


@pytest.mark.asyncio
async def test_get_rank_fallback(player_service, mock_tracker, mock_riot):
    # Tracker rank fails
    mock_tracker.get_lifetime_stats.side_effect = Exception("No stats")
    # Riot rank succeeds
    mock_riot.get_player_by_riot_id.return_value = RiotPlayer(
        puuid="r-123", gameName="T", tagLine="T", region="na"
    )
    mock_riot.get_player_rank.return_value = RiotRank(
        tier="Gold", rank="Gold 2", rankedRating=50
    )

    rank = await player_service.get_rank("Test", "NA1")

    assert rank.tier_name == "Gold"
    assert rank.points == 50


@pytest.mark.asyncio
async def test_get_recent_matches_tracker(player_service, mock_tracker):
    mock_tracker.get_recent_matches.return_value = [
        TrackerMatch(
            matchId="m-1",
            mapName="Ascent",
            agentName="Jett",
            result="Victory",
            kills=20,
            deaths=10,
            assists=5,
            score=5000,
            timestamp="2024-01-01",
        )
    ]

    matches = await player_service.get_recent_matches("Test", "NA1")

    assert len(matches) == 1
    assert matches[0].match_id == "m-1"
    assert matches[0].agent_name == "Jett"


@pytest.mark.asyncio
async def test_health_check_aggregation(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    mock_tracker.health_check.return_value = ProviderHealth(
        status=ProviderStatus.HEALTHY, message="OK", latency_ms=10.0
    )
    mock_henrik.health_check.return_value = ProviderHealth(
        status=ProviderStatus.DEGRADED, message="Slow", latency_ms=500.0
    )
    mock_riot.health_check.return_value = ProviderHealth(
        status=ProviderStatus.UNHEALTHY, message="Down"
    )

    health = await player_service.health()

    assert health["status"] == "degraded"
    assert health["providers"]["tracker"]["status"] == ProviderStatus.HEALTHY
    assert health["providers"]["riot"]["status"] == ProviderStatus.UNHEALTHY
