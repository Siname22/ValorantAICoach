import httpx
import pytest
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.tracker.client import (
    MAX_RETRY_AFTER_SECONDS,
    TrackerHTTPClient,
    parse_retry_after,
)
from backend.providers.tracker.config import TrackerConfig
from backend.providers.tracker.exceptions import (
    TrackerAuthenticationError,
    TrackerNotFound,
    TrackerRateLimit,
    TrackerRateLimitError,
    TrackerServerError,
)
from backend.providers.tracker.models import (
    LifetimeStats,
    MatchSummary,
    PlayerIdentity,
    StatValue,
)
from backend.providers.tracker.provider import TrackerProvider
from pydantic import ValidationError

BASE_URL = "https://api.tracker.gg"
PROFILE_URL = f"{BASE_URL}/profile/riot/Player%23123"


def _stat(value: float, display: str) -> dict:
    return {"value": value, "displayValue": display}


def _profile_payload() -> dict:
    return {
        "data": {
            "platformInfo": {
                "platformId": "riot",
                "platformUserHandle": "Player#123",
                "platformUserIdentifier": "player-id-123",
                "avatarUrl": "https://avatar.url",
            },
            "userInfo": {
                "countryCode": "ES",
                "isPremium": True,
                "isVerified": False,
            },
            "segments": [
                {
                    "type": "overview",
                    "stats": {
                        "kills": _stat(100, "100"),
                        "deaths": _stat(80, "80"),
                        "assists": _stat(20, "20"),
                        "kdRatio": _stat(1.25, "1.25"),
                        "winPct": _stat(55.5, "55.5%"),
                        "headshotPct": _stat(25.0, "25.0%"),
                        "matchesPlayed": _stat(200, "200"),
                        "rank": {
                            "metadata": {
                                "tierName": "Diamond 2",
                                "iconUrl": "https://rank.icon",
                            }
                        },
                    },
                },
                {
                    "type": "weapon",
                    "metadata": {"name": "Vandal"},
                    "stats": {
                        "kills": _stat(500, "500"),
                        "headshotPct": _stat(28.5, "28.5%"),
                        "damagePerRound": _stat(145.2, "145.2"),
                    },
                },
                {
                    "type": "agent",
                    "metadata": {"name": "Jett"},
                    "stats": {
                        "matchesPlayed": _stat(50, "50"),
                        "winRate": _stat(60.0, "60.0%"),
                        "kdRatio": _stat(1.4, "1.4"),
                        "playtime": _stat(180000, "50h"),
                    },
                },
            ],
        }
    }


@pytest.fixture
def tracker_config():
    return TrackerConfig(api_key="test-key", base_url=BASE_URL)


@pytest.fixture
def tracker_provider(tracker_config):
    return TrackerProvider(tracker_config)


# ---------------------------------------------------------------------------
# Configuration & authentication
# ---------------------------------------------------------------------------
def test_config_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("TRACKER_API_KEY", "env-secret-key")
    config = TrackerConfig()
    assert config.api_key == "env-secret-key"
    assert config.base_url == "https://public-api.tracker.gg/v2/valorant/standard"


def test_config_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TRACKER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError):
        TrackerConfig()


@pytest.mark.asyncio
@respx.mock
async def test_client_sends_trn_api_key_header(tracker_config):
    route = respx.get(f"{BASE_URL}/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = TrackerHTTPClient(tracker_config)
    await client.get_json("/ping")
    assert route.called
    request = route.calls.last.request
    assert request.headers["TRN-Api-Key"] == "test-key"
    await client.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_health_check_success(tracker_provider):
    respx.get(f"{BASE_URL}/").mock(return_value=httpx.Response(200))
    health = await tracker_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    assert health.latency_ms is not None
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_health_check_unhealthy(tracker_provider):
    respx.get(f"{BASE_URL}/").mock(side_effect=httpx.ConnectError("down"))
    health = await tracker_provider.health_check()
    assert health.status == ProviderStatus.UNHEALTHY
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Player profile
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_player_success(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    player = await tracker_provider.get_player("riot", "Player#123")
    assert isinstance(player, PlayerIdentity)
    assert player.platform_user_handle == "Player#123"
    assert player.platform_id == "riot"
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_player_profile_success(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    profile = await tracker_provider.get_player_profile("riot", "Player#123")
    assert profile.identity.platform_user_identifier == "player-id-123"
    assert profile.country_code == "ES"
    assert profile.is_premium is True
    assert profile.is_verified is False
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Lifetime stats
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_player_stats_success(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    stats = await tracker_provider.get_player_stats("riot", "Player#123")
    assert isinstance(stats, LifetimeStats)
    assert stats.kills.value == 100
    assert stats.kd_ratio.value == 1.25
    assert stats.matches_played is not None
    assert stats.matches_played.value == 200
    assert stats.rank is not None
    assert stats.rank.tier_name == "Diamond 2"
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_lifetime_stats_alias(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    stats = await tracker_provider.get_lifetime_stats("riot", "Player#123")
    assert stats.headshot_pct.value == 25.0
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Match history
# ---------------------------------------------------------------------------
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
                        "modeName": "Competitive",
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
    respx.get(f"{PROFILE_URL}/matches").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    matches = await tracker_provider.get_recent_matches("riot", "Player#123")
    assert len(matches) == 1
    assert isinstance(matches[0], MatchSummary)
    assert matches[0].match_id == "match-1"
    assert matches[0].map_name == "Ascent"
    assert matches[0].mode_name == "Competitive"
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_match_history_total(tracker_provider):
    mock_data = {"data": {"matches": []}}
    respx.get(f"{PROFILE_URL}/matches").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    history = await tracker_provider.get_match_history("riot", "Player#123")
    assert history.total == 0
    assert history.matches == []
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Weapon & agent segments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_weapon_stats(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    weapons = await tracker_provider.get_weapon_stats("riot", "Player#123")
    assert len(weapons) == 1
    assert weapons[0].name == "Vandal"
    assert weapons[0].kills == 500
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_agent_stats(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(200, json=_profile_payload())
    )
    agents = await tracker_provider.get_agent_stats("riot", "Player#123")
    assert len(agents) == 1
    assert agents[0].name == "Jett"
    assert agents[0].playtime_hours == 50.0
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Season stats
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_get_season_stats(tracker_provider):
    payload = {
        "data": [
            {
                "type": "season",
                "metadata": {"seasonId": "e7a3", "seasonName": "Episode 7 Act 3"},
                "stats": _profile_payload()["data"]["segments"][0]["stats"],
            }
        ]
    }
    respx.get(f"{PROFILE_URL}/segments/season").mock(
        return_value=httpx.Response(200, json=payload)
    )
    season = await tracker_provider.get_season_stats("riot", "Player#123", "e7a3")
    assert season.season_name == "Episode 7 Act 3"
    assert season.stats.kills.value == 100
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_not_found(tracker_provider):
    respx.get(f"{BASE_URL}/profile/riot/NonExistent%23000").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(TrackerNotFound):
        await tracker_provider.get_player("riot", "NonExistent#000")
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_auth_failed(tracker_provider):
    respx.get(PROFILE_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(TrackerAuthenticationError):
        await tracker_provider.get_player("riot", "Player#123")
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_server_error(tracker_provider):
    respx.get(PROFILE_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(TrackerServerError):
        await tracker_provider.get_player("riot", "Player#123")
    await tracker_provider.close()


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@respx.mock
async def test_tracker_error_mapping_rate_limit(tracker_provider):
    respx.get(PROFILE_URL).mock(return_value=httpx.Response(429))
    with pytest.raises(TrackerRateLimit):
        await tracker_provider.get_player("riot", "Player#123")
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_rate_limit_exposes_retry_after(tracker_provider):
    respx.get(PROFILE_URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "2"})
    )
    with pytest.raises(TrackerRateLimitError) as exc_info:
        await tracker_provider.get_player("riot", "Player#123")
    assert exc_info.value.retry_after == 2.0
    assert exc_info.value.status_code == 429
    await tracker_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_tracker_rate_limit_recovers_after_retry(tracker_config):
    config = tracker_config.model_copy(update={"backoff_factor": 0.0})
    provider = TrackerProvider(config)
    route = respx.get(PROFILE_URL)
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json=_profile_payload()),
    ]
    player = await provider.get_player("riot", "Player#123")
    assert player.platform_user_handle == "Player#123"
    assert route.call_count == 2
    await provider.close()


def test_parse_retry_after_seconds():
    assert parse_retry_after("2") == 2.0


def test_parse_retry_after_caps_large_values():
    assert parse_retry_after("3600") == MAX_RETRY_AFTER_SECONDS


def test_parse_retry_after_invalid_returns_none():
    assert parse_retry_after("not-a-date") is None
    assert parse_retry_after(None) is None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def test_stat_value_accepts_alias_and_field_name():
    from_alias = StatValue.model_validate({"value": 1.0, "displayValue": "1"})
    from_name = StatValue.model_validate({"value": 1.0, "display_value": "1"})
    assert from_alias.display_value == from_name.display_value == "1"


def test_lifetime_stats_requires_core_fields():
    with pytest.raises(ValidationError):
        LifetimeStats.model_validate({"kills": {"value": 1, "displayValue": "1"}})


def test_match_summary_serialization_roundtrip():
    match = MatchSummary(
        match_id="m1",
        map_name="Bind",
        agent_name="Sova",
        result="Loss",
        kills=10,
        deaths=12,
        assists=3,
        score=2500,
        timestamp="2023-01-01T12:00:00Z",
    )
    dumped = match.model_dump(by_alias=True)
    assert dumped["matchId"] == "m1"
    assert MatchSummary.model_validate(dumped) == match
