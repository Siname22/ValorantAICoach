import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.player_service import PlayerService, PlayerIdentity, PlayerRank, PlayerStatsOverview, PlayerNotFoundError, PlayerServiceError
from backend.providers.riot.models import Player as RiotPlayer, Rank as RiotRank, Match as RiotMatch, MatchPlayerStats
from backend.providers.tracker.models import Player as TrackerPlayerModel, LifetimeStats as TrackerStats, PlayerIdentity as TrackerIdentity, Rank as TrackerRank, StatValue, MatchSummary as TrackerMatch

@pytest.fixture
def mock_riot():
    provider = MagicMock()
    provider.get_player_by_riot_id = AsyncMock()
    provider.get_player_match_history = AsyncMock()
    provider.get_player_rank = AsyncMock()
    provider.close = AsyncMock()
    return provider

@pytest.fixture
def mock_henrik():
    provider = MagicMock()
    provider.get_account = AsyncMock()
    provider.get_matches = AsyncMock()
    provider.close = AsyncMock()
    return provider

@pytest.fixture
def mock_tracker():
    provider = MagicMock()
    provider.get_player_profile = AsyncMock()
    provider.get_lifetime_stats = AsyncMock()
    provider.get_recent_matches = AsyncMock()
    provider.close = AsyncMock()
    return provider

@pytest.fixture
def player_service(mock_riot, mock_henrik, mock_tracker):
    return PlayerService(mock_riot, mock_henrik, mock_tracker)

@pytest.mark.asyncio
async def test_get_player_identity_tracker_priority(player_service, mock_tracker):
    # Setup
    mock_identity = TrackerIdentity(
        platformId="riot", platformUserHandle="Test#NA1", platformUserIdentifier="t-123", avatarUrl="http://avatar.url"
    )
    mock_tracker.get_player_profile.return_value = TrackerPlayerModel(identity=mock_identity)
    
    # Execute
    identity = await player_service.get_player_identity("Test", "NA1")
    
    # Assert
    assert identity.game_name == "Test"
    assert identity.avatar_url == "http://avatar.url"
    assert identity.source == "tracker"
    mock_tracker.get_player_profile.assert_called_once()

@pytest.mark.asyncio
async def test_get_player_identity_fallback_to_riot(player_service, mock_tracker, mock_henrik, mock_riot):
    # Setup: Tracker and Henrik fail
    mock_tracker.get_player_profile.side_effect = Exception("Tracker Down")
    mock_henrik.get_account.side_effect = Exception("Henrik Down")
    mock_riot.get_player_by_riot_id.return_value = RiotPlayer(
        puuid="riot-123", gameName="Test", tagLine="NA1", region="na", accountLevel=50
    )
    
    # Execute
    identity = await player_service.get_player_identity("Test", "NA1")
    
    # Assert
    assert identity.puuid == "riot-123"
    assert identity.source == "riot"

@pytest.mark.asyncio
async def test_get_player_identity_all_fail(player_service, mock_tracker, mock_henrik, mock_riot):
    # Setup: All fail
    mock_tracker.get_player_profile.side_effect = Exception("Fail")
    mock_henrik.get_account.side_effect = Exception("Fail")
    mock_riot.get_player_by_riot_id.side_effect = Exception("Fail")
    
    # Execute & Assert
    with pytest.raises(PlayerServiceError):
        await player_service.get_player_identity("Test", "NA1")

@pytest.mark.asyncio
async def test_get_rank_tracker_success(player_service, mock_tracker):
    # Setup
    mock_tracker.get_lifetime_stats.return_value = TrackerStats(
        kills=StatValue(value=10, displayValue="10"),
        deaths=StatValue(value=5, displayValue="5"),
        assists=StatValue(value=2, displayValue="2"),
        kdRatio=StatValue(value=2.0, displayValue="2.0"),
        winPct=StatValue(value=50.0, displayValue="50%"),
        headshotPct=StatValue(value=20.0, displayValue="20%"),
        rank=TrackerRank(tier_name="Diamond 1", icon_url="http://icon.url", points=50)
    )
    
    # Execute
    rank = await player_service.get_rank("Test", "NA1")
    
    # Assert
    assert rank.tier_name == "Diamond 1"
    assert rank.source == "tracker"

@pytest.mark.asyncio
async def test_get_stats_overview(player_service, mock_tracker):
    # Setup
    mock_tracker.get_lifetime_stats.return_value = TrackerStats(
        kills=StatValue(value=100, displayValue="100"),
        deaths=StatValue(value=50, displayValue="50"),
        assists=StatValue(value=25, displayValue="25"),
        kdRatio=StatValue(value=2.0, displayValue="2.0"),
        winPct=StatValue(value=60.0, displayValue="60%"),
        headshotPct=StatValue(value=25.0, displayValue="25%"),
        matchesPlayed=StatValue(value=10, displayValue="10")
    )
    
    # Execute
    stats = await player_service.get_stats_overview("Test", "NA1")
    
    # Assert
    assert stats.kills == 100
    assert stats.kd_ratio == 2.0
    assert stats.matches_played == 10

@pytest.mark.asyncio
async def test_get_complete_player_profile(player_service, mock_riot, mock_tracker):
    # Setup
    mock_riot.get_player_by_riot_id.return_value = RiotPlayer(
        puuid="r-123", gameName="Test", tagLine="NA1", region="na", accountLevel=10
    )
    mock_tracker.get_lifetime_stats.side_effect = Exception("No stats")
    mock_tracker.get_recent_matches.return_value = []
    
    # Execute
    profile = await player_service.get_complete_player_profile("Test", "NA1")
    
    # Assert
    assert profile.identity.puuid == "r-123"
    assert profile.stats is None
    assert profile.rank is None
    assert len(profile.recent_matches) == 0
