import httpx
import pytest
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.tracker.config import TrackerConfig
from backend.providers.tracker.exceptions import (
    TrackerAuthenticationError,
    TrackerNotFound,
    TrackerRateLimit,
)
from backend.providers.tracker.provider import TrackerProvider


@pytest.fixture
def tracker_config():
    return TrackerConfig(api_key="test-key", base_url="https://api.tracker.gg")


@pytest.fixture
def tracker_provider(tracker_config):
    return TrackerProvider(tracker_config)


@pytest.mark.asyncio
@respx.mock
async def test_tracker_health_check_success(tracker_provider):
    respx.get("https://api.tracker.gg/").mock(return_value=httpx.Response(200))
    health = await tracker_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_player_success(tracker_provider):
    mock_data = {
        "data": {
            "platformInfo": {
                "platformId": "riot",
                "platformUserHandle": "Player#123",
                "platformUserIdentifier": "player-id-123",
                "avatarUrl": "https://avatar.url",
            }
        }
    }
    respx.get("https://api.tracker.gg/profile/riot/Player%23123").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    player = await tracker_provider.get_player("riot", "Player#123")
    assert player.platform_user_handle == "Player#123"
    assert player.platform_id == "riot"
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_player_stats_success(tracker_provider):
    mock_data = {
        "data": {
            "segments": [
                {
                    "stats": {
                        "kills": {"value": 100, "displayValue": "100"},
                        "deaths": {"value": 80, "displayValue": "80"},
                        "assists": {"value": 20, "displayValue": "20"},
                        "kdRatio": {"value": 1.25, "displayValue": "1.25"},
                        "winPct": {"value": 55.5, "displayValue": "55.5%"},
                        "headshotPct": {"value": 25.0, "displayValue": "25.0%"},
                    }
                }
            ]
        }
    }
    respx.get("https://api.tracker.gg/profile/riot/Player%23123").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    stats = await tracker_provider.get_player_stats("riot", "Player#123")
    assert stats.kills.value == 100
    assert stats.kd_ratio.value == 1.25
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_recent_matches_success(tracker_provider):
    mock_data = {
        "data": {
            "matches": [
                {
                    "attributes": {"matchId": "match-1"},
                    "metadata": {
                        "mapName": "Ascent",
                        "agentName": "Jett",
                        "result": "Win",
                        "timestamp": "2023-01-01T12:00:00Z",
                    },
                    "stats": {
                        "kills": {"value": 20},
                        "deaths": {"value": 15},
                        "assists": {"value": 5},
                        "score": {"value": 4000},
                    },
                }
            ]
        }
    }
    respx.get("https://api.tracker.gg/profile/riot/Player%23123/matches").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    matches = await tracker_provider.get_recent_matches("riot", "Player#123")
    assert len(matches) == 1
    assert matches[0].match_id == "match-1"
    assert matches[0].map_name == "Ascent"
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_not_found(tracker_provider):
    respx.get("https://api.tracker.gg/profile/riot/NonExistent%23000").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(TrackerNotFound):
        await tracker_provider.get_player("riot", "NonExistent#000")
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_auth_failed(tracker_provider):
    respx.get("https://api.tracker.gg/profile/riot/Player%23123").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(TrackerAuthenticationError):
        await tracker_provider.get_player("riot", "Player#123")
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_rate_limit(tracker_provider):
    respx.get("https://api.tracker.gg/profile/riot/Player%23123").mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(TrackerRateLimit):
        await tracker_provider.get_player("riot", "Player#123")
    await tracker_provider.close()
