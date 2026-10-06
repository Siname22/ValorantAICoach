import os
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.riot.config import RiotConfig
from backend.providers.riot.exceptions import (
    RiotAuthenticationError,
    RiotError,
    RiotNotFoundError,
    RiotRateLimitError,
)
from backend.providers.riot.provider import RiotProvider
from pydantic import ValidationError

ACCOUNT_URL = "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id"
SHARD_URL = "https://eu.api.riotgames.com"


@pytest.fixture(autouse=True)
def isolate_riot_environment(monkeypatch):
    for name in os.environ:
        if name.startswith("RIOT_"):
            monkeypatch.delenv(name)


@pytest.fixture
def riot_config():
    return RiotConfig(api_key="test-riot-key", retries=0, _env_file=None)


@pytest_asyncio.fixture
async def riot_provider(riot_config):
    provider = RiotProvider(riot_config)
    try:
        yield provider
    finally:
        await provider.close()


@pytest.fixture
def match_detail():
    return {
        "matchInfo": {
            "matchId": "match-1",
            "mapId": "/Game/Maps/Ascent/Ascent",
            "gameMode": "/Game/GameModes/Bomb/BombGameMode.BombGameMode_C",
            "queueId": "competitive",
            "gameStartMillis": 1712345678000,
            "gameLengthMillis": 1800000,
            "isCompleted": True,
            "isRanked": True,
        },
        "players": [
            {
                "puuid": "another-player",
                "teamId": "Red",
                "characterId": "other-agent-id",
                "stats": {
                    "kills": 99,
                    "deaths": 1,
                    "assists": 0,
                    "score": 9900,
                    "roundsPlayed": 20,
                },
            },
            {
                "puuid": "account-puuid",
                "teamId": "Blue",
                "characterId": "add6443a-41bd-e414-f6ad-e58d267f4e95",
                "stats": {
                    "kills": 23,
                    "deaths": 7,
                    "assists": 4,
                    "score": 4321,
                    "roundsPlayed": 20,
                },
            },
        ],
        "teams": [
            {"teamId": "Red", "won": False, "roundsPlayed": 20, "roundsWon": 7},
            {"teamId": "Blue", "won": True, "roundsPlayed": 20, "roundsWon": 13},
        ],
        "roundResults": [],
    }


def test_riot_defaults_use_europe_hosts_and_bounded_history():
    config = RiotConfig(api_key="test-riot-key", _env_file=None)

    assert config.region == "eu"
    assert config.base_url == "https://eu.api.riotgames.com"
    assert config.account_base_url == "https://europe.api.riotgames.com"
    assert config.match_history_limit == 10


def test_riot_config_accepts_no_key_and_reads_only_riot_environment(monkeypatch):
    monkeypatch.setenv("API_KEY", "other-provider-key")
    assert RiotConfig(_env_file=None).api_key is None

    monkeypatch.setenv("RIOT_API_KEY", "configured-riot-key")
    monkeypatch.setenv("RIOT_REGION", "na")
    monkeypatch.setenv("RIOT_ACCOUNT_BASE_URL", "https://americas.api.riotgames.com")
    monkeypatch.setenv("RIOT_MATCH_HISTORY_LIMIT", "3")
    monkeypatch.setenv("RIOT_ENABLED", "false")
    config = RiotConfig(_env_file=None)

    assert config.api_key == "configured-riot-key"
    assert config.region == "na"
    assert config.base_url == "https://na.api.riotgames.com"
    assert config.account_base_url == "https://americas.api.riotgames.com"
    assert config.match_history_limit == 3
    assert config.enabled is False


@pytest.mark.parametrize("limit", [0, -1, 21, 500])
def test_riot_config_rejects_unbounded_history(limit):
    with pytest.raises(ValidationError):
        RiotConfig(api_key="test-riot-key", match_history_limit=limit, _env_file=None)


@pytest.mark.parametrize("region", ["euw1", "unknown", "", "eu/other"])
def test_riot_config_rejects_unsupported_shards(region):
    with pytest.raises(ValidationError):
        RiotConfig(api_key="test-riot-key", region=region, _env_file=None)


def test_riot_config_preserves_explicit_shard_host():
    config = RiotConfig(
        api_key="test-riot-key",
        region="na",
        base_url="https://custom.api.riotgames.com",
        _env_file=None,
    )
    assert config.base_url == "https://custom.api.riotgames.com"


@pytest.mark.asyncio
@respx.mock
async def test_riot_account_uses_official_data_and_token_header(riot_provider):
    route = respx.get(f"{ACCOUNT_URL}/Player/123").respond(
        200,
        json={"puuid": "account-puuid", "gameName": "PLAYER", "tagLine": "EUW"},
    )

    player = await riot_provider.get_player_by_riot_id("Player", "123")

    assert player.puuid == "account-puuid"
    assert player.game_name == "PLAYER"
    assert player.tag_line == "EUW"
    assert player.region == "eu"
    assert player.account_level is None
    assert route.call_count == 1
    request = route.calls.last.request
    assert request.headers["X-Riot-Token"] == "test-riot-key"
    assert "X-API-Key" not in request.headers
    assert "api_key" not in request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_riot_account_uses_requested_identity_when_names_are_omitted(
    riot_provider,
):
    respx.get(f"{ACCOUNT_URL}/Player/123").respond(200, json={"puuid": "account-puuid"})

    player = await riot_provider.get_player_by_riot_id("Player", "123")

    assert player.puuid == "account-puuid"
    assert player.game_name == "Player"
    assert player.tag_line == "123"
    assert player.account_level is None


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (404, RiotNotFoundError),
        (401, RiotAuthenticationError),
        (403, RiotAuthenticationError),
        (429, RiotRateLimitError),
        (500, RiotError),
    ],
)
async def test_riot_account_propagates_http_errors(
    riot_provider, status_code, error_type
):
    route = respx.get(f"{ACCOUNT_URL}/Player/123").respond(
        status_code, text="upstream error"
    )

    with pytest.raises(error_type) as error:
        await riot_provider.get_player_by_riot_id("Player", "123")

    assert error.value.status_code == status_code
    assert error.value.response_body == "upstream error"
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"puuid": None},
        {"puuid": ""},
        [],
        {"puuid": "account-puuid", "gameName": 123},
        {"puuid": "account-puuid", "tagLine": ["EU"]},
    ],
)
async def test_riot_account_rejects_incomplete_payload(riot_provider, payload):
    respx.get(f"{ACCOUNT_URL}/Player/123").respond(200, json=payload)

    with pytest.raises(RiotError, match="account"):
        await riot_provider.get_player_by_riot_id("Player", "123")


@pytest.mark.asyncio
@respx.mock
async def test_riot_account_rejects_invalid_json(riot_provider):
    respx.get(f"{ACCOUNT_URL}/Player/123").respond(200, text="<html>unavailable</html>")

    with pytest.raises(RiotError, match="JSON"):
        await riot_provider.get_player_by_riot_id("Player", "123")


@pytest.mark.asyncio
@respx.mock
async def test_riot_account_escapes_each_identity_segment_once(riot_provider):
    path = "/Pl%C3%A4yer%20%2F%25%3F%23/EU%20%2F%25%3F%23"
    route = respx.get(f"{ACCOUNT_URL}{path}").respond(
        200, json={"puuid": "account-puuid"}
    )

    player = await riot_provider.get_player_by_riot_id("Pl\u00e4yer /%?#", "EU /%?#")

    assert player.puuid == "account-puuid"
    assert route.calls.last.request.url.raw_path == (
        b"/riot/account/v1/accounts/by-riot-id" + path.encode("ascii")
    )


@pytest.mark.asyncio
@respx.mock
async def test_riot_health_uses_official_platform_status(riot_provider):
    route = respx.get(f"{SHARD_URL}/val/status/v1/platform-data").respond(
        200,
        json={"id": "eu", "name": "Europe", "maintenances": [], "incidents": []},
    )

    health = await riot_provider.health_check()

    assert health.status == ProviderStatus.HEALTHY
    assert route.call_count == 1
    assert route.calls.last.request.headers["X-Riot-Token"] == "test-riot-key"
    assert "X-API-Key" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("status_code", [403, 429, 503])
async def test_riot_health_reports_upstream_errors(riot_provider, status_code):
    route = respx.get(f"{SHARD_URL}/val/status/v1/platform-data").respond(status_code)

    health = await riot_provider.health_check()

    assert health.status == ProviderStatus.UNHEALTHY
    assert str(status_code) in health.message
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_riot_player_rank_is_explicitly_unsupported(riot_provider):
    with pytest.raises(NotImplementedError, match="official Riot API"):
        await riot_provider.get_player_rank("account-puuid")

    assert len(respx.calls) == 0


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_fetches_real_details_for_selected_player(
    riot_provider, match_detail
):
    history = respx.get(
        f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid"
    ).respond(
        200,
        json={
            "puuid": "account-puuid",
            "history": [{"matchId": "match-1", "gameStartTimeMillis": 1712345678000}],
        },
    )
    detail = respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(
        200, json=match_detail
    )

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 1
    match = matches[0]
    assert match.match_id == "match-1"
    assert match.map_id == "/Game/Maps/Ascent/Ascent"
    assert match.game_mode == "/Game/GameModes/Bomb/BombGameMode.BombGameMode_C"
    assert match.game_start_time == 1712345678000
    assert match.result == "Victory"
    assert match.player_stats.kills == 23
    assert match.player_stats.deaths == 7
    assert match.player_stats.assists == 4
    assert match.player_stats.score == 4321
    assert match.player_stats.acs == pytest.approx(216.05)
    assert match.player_stats.agent_name == "add6443a-41bd-e414-f6ad-e58d267f4e95"
    assert history.call_count == 1
    assert detail.call_count == 1
    for request in [history.calls.last.request, detail.calls.last.request]:
        assert request.headers["X-Riot-Token"] == "test-riot-key"
        assert "X-API-Key" not in request.headers


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_caps_detail_calls_even_for_large_matchlist(
    riot_provider, match_detail
):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200,
        json={"history": [{"matchId": f"match-{index}"} for index in range(500)]},
    )
    routes = []
    for index in range(10):
        payload = {
            **match_detail,
            "matchInfo": {**match_detail["matchInfo"], "matchId": f"match-{index}"},
        }
        routes.append(
            respx.get(f"{SHARD_URL}/val/match/v1/matches/match-{index}").respond(
                200, json=payload
            )
        )

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 10
    assert matches[0].match_id == "match-0"
    assert matches[-1].match_id == "match-9"
    assert all(route.call_count == 1 for route in routes)
    assert len(respx.calls) == 11


@pytest.mark.asyncio
@respx.mock
async def test_riot_get_match_returns_official_detail(riot_provider, match_detail):
    route = respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(
        200, json=match_detail
    )

    get_match = getattr(riot_provider, "get_match", None)
    assert get_match is not None
    detail = await get_match("match-1")

    assert detail == match_detail
    assert route.call_count == 1
    assert route.calls.last.request.headers["X-Riot-Token"] == "test-riot-key"


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("limit", [1, 2, 20])
async def test_riot_history_accepts_requested_limit(riot_provider, match_detail, limit):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": [{"matchId": f"match-{index}"} for index in range(25)]}
    )
    for index in range(limit):
        payload = {
            **match_detail,
            "matchInfo": {**match_detail["matchInfo"], "matchId": f"match-{index}"},
        }
        respx.get(f"{SHARD_URL}/val/match/v1/matches/match-{index}").respond(
            200, json=payload
        )

    matches = await riot_provider.get_player_match_history("account-puuid", limit=limit)

    assert len(matches) == limit
    assert len(respx.calls) == limit + 1


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("limit", [0, -1, 21, 500])
async def test_riot_history_rejects_invalid_requested_limit(riot_provider, limit):
    with pytest.raises(ValueError, match="limit"):
        await riot_provider.get_player_match_history("account-puuid", limit=limit)

    assert len(respx.calls) == 0


def mock_single_match(detail):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": [{"matchId": "match-1"}]}
    )
    return respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(
        200, json=detail
    )


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_handles_explicit_empty_history(riot_provider):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": []}
    )

    assert await riot_provider.get_player_match_history("account-puuid") == []
    assert len(respx.calls) == 1


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "payload", [{}, {"history": None}, {"history": {"matchId": "match-1"}}]
)
async def test_riot_history_rejects_malformed_history(riot_provider, payload):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json=payload
    )

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_skips_invalid_matchlist_entries(riot_provider):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": [{}, {"matchId": None}, {"matchId": ""}, "invalid"]}
    )

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")
    assert len(respx.calls) == 1


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_skips_match_without_requested_player(
    riot_provider, match_detail
):
    match_detail["players"] = [match_detail["players"][0]]
    route = mock_single_match(match_detail)

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("incomplete", ["stats", "characterId", "matchInfo"])
async def test_riot_history_skips_incomplete_player_or_match(
    riot_provider, match_detail, incomplete
):
    if incomplete == "matchInfo":
        match_detail.pop("matchInfo")
    else:
        match_detail["players"][1].pop(incomplete)
    mock_single_match(match_detail)

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("stats", [None, "invalid", {"kills": "invalid"}])
async def test_riot_history_skips_malformed_player_stats(
    riot_provider, match_detail, stats
):
    match_detail["players"][1]["stats"] = stats
    mock_single_match(match_detail)

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("stats", "score", "acs"),
    [
        ({"roundsPlayed": 20}, 0, 0.0),
        (
            {"kills": 0, "deaths": 0, "assists": 0, "score": 400, "roundsPlayed": 0},
            400,
            None,
        ),
    ],
)
async def test_riot_history_preserves_omitted_zero_stats_without_inventing_acs(
    riot_provider, match_detail, stats, score, acs
):
    match_detail["players"][1]["stats"] = stats
    mock_single_match(match_detail)

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 1
    assert matches[0].player_stats.kills == 0
    assert matches[0].player_stats.deaths == 0
    assert matches[0].player_stats.assists == 0
    assert matches[0].player_stats.score == score
    assert matches[0].player_stats.acs == acs


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("teams", "expected"),
    [
        ([{"teamId": "Blue", "won": False}, {"teamId": "Red", "won": True}], "Defeat"),
        ([{"teamId": "Blue", "won": False}, {"teamId": "Red", "won": False}], "Draw"),
        ([{"teamId": "Blue"}], "Unknown"),
        ([], "Unknown"),
    ],
)
async def test_riot_history_uses_team_outcome_or_unknown(
    riot_provider, match_detail, teams, expected
):
    match_detail["teams"] = teams
    mock_single_match(match_detail)

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 1
    assert matches[0].result == expected


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("operation", ["history", "match"])
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (404, RiotNotFoundError),
        (401, RiotAuthenticationError),
        (429, RiotRateLimitError),
    ],
)
async def test_riot_match_operations_propagate_http_errors(
    riot_provider, operation, status_code, error_type
):
    if operation == "history":
        url = f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid"
        fetch = riot_provider.get_player_match_history
        identity = "account-puuid"
    else:
        url = f"{SHARD_URL}/val/match/v1/matches/match-1"
        fetch = riot_provider.get_match
        identity = "match-1"
    route = respx.get(url).respond(status_code)

    with pytest.raises(error_type) as error:
        await fetch(identity)

    assert error.value.status_code == status_code
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_propagates_rate_limit_from_match_detail(riot_provider):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": [{"matchId": "match-1"}, {"matchId": "match-2"}]}
    )
    route = respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(
        429, headers={"Retry-After": "60"}
    )

    with pytest.raises(RiotRateLimitError) as error:
        await riot_provider.get_player_match_history("account-puuid")

    assert error.value.status_code == 429
    assert route.call_count == 1
    assert len(respx.calls) == 2


@pytest.mark.asyncio
@respx.mock
async def test_riot_shard_identity_segments_are_escaped_once(riot_provider):
    history = respx.get(
        f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/puuid%2F%25%3F%23"
    ).respond(200, json={"history": []})
    detail = respx.get(f"{SHARD_URL}/val/match/v1/matches/match%2F%25%3F%23").respond(
        200, json={"matchInfo": {"matchId": "match/%?#"}}
    )

    assert await riot_provider.get_player_match_history("puuid/%?#") == []
    match = await riot_provider.get_match("match/%?#")

    assert match["matchInfo"]["matchId"] == "match/%?#"
    assert history.calls.last.request.url.raw_path == (
        b"/val/match/v1/matchlists/by-puuid/puuid%2F%25%3F%23"
    )
    assert detail.calls.last.request.url.raw_path == (
        b"/val/match/v1/matches/match%2F%25%3F%23"
    )


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_continues_after_missing_player(riot_provider, match_detail):
    respx.get(f"{SHARD_URL}/val/match/v1/matchlists/by-puuid/account-puuid").respond(
        200, json={"history": [{"matchId": "absent-player"}, {"matchId": "match-1"}]}
    )
    respx.get(f"{SHARD_URL}/val/match/v1/matches/absent-player").respond(
        200, json={**match_detail, "players": []}
    )
    respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(
        200, json=match_detail
    )

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 1
    assert matches[0].match_id == "match-1"
    assert len(respx.calls) == 3


@pytest.mark.asyncio
@respx.mock
async def test_riot_incomplete_match_info_does_not_invent_a_draw(
    riot_provider, match_detail
):
    match_detail["matchInfo"] = None
    match_detail["teams"][1]["won"] = False
    mock_single_match(match_detail)

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"matchInfo": None},
        {"matchInfo": {}},
        {"matchInfo": {"matchId": ""}},
        {"matchInfo": {"matchId": 123}},
        [],
    ],
)
async def test_riot_get_match_rejects_corrupt_detail(riot_provider, payload):
    respx.get(f"{SHARD_URL}/val/match/v1/matches/match-1").respond(200, json=payload)

    with pytest.raises(RiotError, match="match|matches"):
        await riot_provider.get_match("match-1")


@pytest.mark.asyncio
@respx.mock
async def test_riot_history_rejects_empty_stats_instead_of_inventing_them(
    riot_provider, match_detail
):
    match_detail["players"][1]["stats"] = {}
    mock_single_match(match_detail)

    with pytest.raises(RiotError, match="history"):
        await riot_provider.get_player_match_history("account-puuid")


@pytest.mark.asyncio
@respx.mock
async def test_riot_health_does_not_expose_error_body(riot_provider):
    respx.get(f"{SHARD_URL}/val/status/v1/platform-data").respond(
        403, text="private upstream details: test-riot-key"
    )

    health = await riot_provider.health_check()

    assert health.status == ProviderStatus.UNHEALTHY
    assert "403" in health.message
    assert "private upstream details" not in health.message
    assert "test-riot-key" not in health.message


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("retry_after", "expected_wait"),
    [("2", 2.0), ("0", 0.0), ("invalid", 0.5), ("-1", 0.5), ("nan", 0.5)],
)
async def test_riot_rate_limit_retry_respects_valid_retry_after(
    riot_provider, riot_config, monkeypatch, retry_after, expected_wait
):
    riot_config.retries = 1
    sleep = AsyncMock()
    monkeypatch.setattr("backend.providers.base.client.asyncio.sleep", sleep)
    route = respx.get(f"{ACCOUNT_URL}/Player/123").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": retry_after}),
            httpx.Response(200, json={"puuid": "account-puuid"}),
        ]
    )

    player = await riot_provider.get_player_by_riot_id("Player", "123")

    assert player.puuid == "account-puuid"
    assert route.call_count == 2
    sleep.assert_awaited_once_with(expected_wait)


@pytest.mark.asyncio
@respx.mock
async def test_riot_missing_team_identity_cannot_be_reported_as_a_win(
    riot_provider, match_detail
):
    match_detail["players"][1].pop("teamId")
    match_detail["teams"] = [{"won": True}]
    mock_single_match(match_detail)

    matches = await riot_provider.get_player_match_history("account-puuid")

    assert len(matches) == 1
    assert matches[0].result == "Unknown"
