from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.services.player_service import (
    PlayerNotFoundError,
    PlayerService,
    PlayerServiceError,
)
from backend.providers.base.exceptions import NotFoundError, ServerError
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.henrik.models import (
    HenrikPlayer,
)
from backend.providers.riot.models import Player as RiotPlayer
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
async def test_get_rank_fallback(player_service, mock_tracker, mock_henrik):
    # Tracker rank fails
    mock_tracker.get_lifetime_stats.side_effect = Exception("No stats")
    # Rank comes from Henrik; Riot does not expose per-player current RR.
    mock_henrik.get_account.return_value = HenrikPlayer(
        puuid="h-123", name="Test", tag="NA1", region="na", account_level=20
    )
    mock_henrik.get_rank = AsyncMock(
        return_value=SimpleNamespace(tier_name="Gold 2", rank_icon_url=None, points=50)
    )

    rank = await player_service.get_rank("Test", "NA1")

    assert rank.tier_name == "Gold 2"
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


@pytest.mark.asyncio
async def test_outage_is_not_reported_as_player_not_found(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    mock_tracker.get_player_profile.side_effect = ServerError("upstream-private-body")
    mock_henrik.get_account.side_effect = NotFoundError("missing")
    mock_riot.get_player_by_riot_id.side_effect = NotFoundError("missing")
    with pytest.raises(PlayerServiceError) as error:
        await player_service.get_player("Test", "EU1")
    assert not isinstance(error.value, PlayerNotFoundError)
    assert "upstream-private-body" not in str(error.value)


@pytest.mark.asyncio
async def test_match_outage_does_not_return_empty_history(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    mock_tracker.get_recent_matches.side_effect = ServerError("offline")
    mock_henrik.get_account.side_effect = ServerError("offline")
    mock_henrik.get_matches.side_effect = ServerError("offline")
    mock_riot.get_player_by_riot_id.side_effect = ServerError("offline")
    with pytest.raises(PlayerServiceError):
        await player_service.get_recent_matches("Test", "EU1")


@pytest.mark.asyncio
async def test_henrik_history_uses_account_region_and_real_stats(
    player_service, mock_tracker, mock_henrik
):
    mock_tracker.get_recent_matches.side_effect = ServerError("offline")
    mock_henrik.get_account.return_value = HenrikPlayer(
        puuid="h-123", name="Test", tag="EU1", region="eu", account_level=20
    )
    mock_henrik.get_matches.return_value = [
        SimpleNamespace(
            metadata=SimpleNamespace(
                id="eu-match",
                map=SimpleNamespace(name="Ascent"),
                mode="Competitive",
                time="2026-10-04T12:00:00Z",
            ),
            stats=SimpleNamespace(
                kills=24,
                deaths=12,
                assists=7,
                score=6000,
                team="Red",
                character=SimpleNamespace(name="Jett"),
            ),
            teams=SimpleNamespace(red=13, blue=7),
        )
    ]
    matches = await player_service.get_recent_matches("Test", "EU1")
    mock_henrik.get_matches.assert_awaited_once_with("eu", "Test", "EU1")
    assert matches[0].match_id == "eu-match"
    assert matches[0].kills == 24
    assert matches[0].deaths == 12
    assert matches[0].assists == 7
    assert matches[0].score is None
    assert getattr(matches[0], "provider_score", None) == 6000
    assert getattr(matches[0], "provider", None) == "henrik"
    assert matches[0].agent_name == "Jett"
    assert matches[0].result == "Victory"


@pytest.mark.asyncio
async def test_rank_can_use_henrik_without_riot_or_tracker(mock_henrik):
    mock_henrik.get_account.return_value = HenrikPlayer(
        puuid="h-123", name="Test", tag="EU1", region="eu", account_level=20
    )
    mock_henrik.get_rank = AsyncMock(
        return_value=SimpleNamespace(
            tier_name="Diamond 2", rank_icon_url=None, points=42
        )
    )
    service = PlayerService(None, mock_henrik, None)
    rank = await service.get_rank("Test", "EU1")
    assert rank.tier_name == "Diamond 2"
    assert rank.points == 42
    mock_henrik.get_rank.assert_awaited_once_with("eu", "Test", "EU1")


@pytest.mark.asyncio
async def test_health_isolates_provider_exception(
    player_service, mock_tracker, mock_henrik, mock_riot
):
    mock_tracker.health_check.side_effect = RuntimeError("private-response")
    mock_henrik.health_check.return_value = ProviderHealth(
        status=ProviderStatus.HEALTHY
    )
    mock_riot.health_check.return_value = ProviderHealth(status=ProviderStatus.HEALTHY)
    health = await player_service.health()
    assert health["status"] == "degraded"
    assert health["providers"]["tracker"]["status"] == "unhealthy"
    assert "private-response" not in health["providers"]["tracker"]["message"]


@pytest.mark.asyncio
async def test_get_recent_matches_riot_resolves_map_and_agent_names(mock_riot):
    from backend.providers.riot.models import Match as RiotMatch
    from backend.providers.riot.models import MatchPlayerStats

    mock_riot.get_player_match_history.return_value = [
        RiotMatch(
            matchId="riot-match-1",
            mapId="/Game/Maps/Ascent/Ascent",
            gameMode="Competitive",
            gameStartTimeMillis=1700000000000,
            result="Victory",
            player_stats=MatchPlayerStats(
                kills=22,
                deaths=10,
                assists=5,
                score=4500,
                character="add6443a-41bd-e414-f6ad-e58d267f4e95",
            ),
        )
    ]
    service = PlayerService(mock_riot, None, None)
    matches = await service.get_recent_matches("Player", "Tag", puuid="test-puuid")

    assert len(matches) == 1
    assert matches[0].match_id == "riot-match-1"
    assert matches[0].map_name == "Ascent"
    assert matches[0].agent_name == "Jett"
    assert matches[0].provider == "riot"
