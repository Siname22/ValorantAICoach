import httpx
import pytest
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.henrik.config import HenrikConfig
from backend.providers.henrik.exceptions import (
    HenrikAuthenticationError,
    HenrikError,
    HenrikNotFoundError,
    HenrikRateLimitError,
)
from backend.providers.henrik.provider import HenrikProvider
from pydantic import ValidationError


@pytest.fixture
def henrik_config():
    return HenrikConfig(
        api_key="test-henrik-key",
        base_url="https://api.henrikdev.xyz/valorant/v1",
        retries=0,
        _env_file=None,
    )


@pytest.fixture
def henrik_provider(henrik_config):
    return HenrikProvider(henrik_config)


@pytest.fixture
def account_response():
    return {
        "status": 200,
        "data": {
            "puuid": "test-puuid",
            "name": "Player",
            "tag": "123",
            "region": "eu",
            "account_level": 50,
            "card": {
                "id": "card-uuid",
                "small": "https://example.com/card-small.png",
                "large": "https://example.com/card-large.png",
                "wide": "https://example.com/card-wide.png",
            },
            "last_update": "1 minute ago",
            "last_update_raw": 1783686896,
        },
    }


@pytest.fixture
def lifetime_match():
    return {
        "metadata": {
            "id": "match-uuid",
            "map": {"id": "map-uuid", "name": "Ascent"},
            "version": "release-10.00-shipping-12-3456789",
            "mode": "Competitive",
            "time": "2026-07-10T12:34:56Z",
            "season": {"id": "season-uuid", "short": "E10A5"},
            "region": "eu",
            "cluster": "Frankfurt",
        },
        "stats": {
            "puuid": "test-puuid",
            "name": "Player",
            "tag": "123",
            "team": "Blue",
            "level": 150,
            "character": {"id": "agent-uuid", "name": "Jett"},
            "tier": 22,
            "score": 250,
            "kills": 20,
            "deaths": 15,
            "assists": 5,
            "shots": {"head": 10, "body": 40, "leg": 5},
            "damage": {"made": 3200, "received": 2800},
        },
        "teams": {"red": 13, "blue": 9},
    }


@pytest.fixture
def mmr_response():
    return {
        "status": 200,
        "data": {
            "name": "Player",
            "tag": "123",
            "puuid": "test-puuid",
            "current_data": {
                "currenttier": 19,
                "currenttierpatched": "Diamond 2",
                "images": {
                    "small": "https://example.com/diamond-small.png",
                    "large": "https://example.com/diamond-large.png",
                    "triangle_down": "https://example.com/diamond-down.png",
                    "triangle_up": "https://example.com/diamond-up.png",
                },
                "ranking_in_tier": 67,
                "mmr_change_to_last_game": 28,
                "elo": 1667,
                "games_needed_for_rating": 0,
                "old": False,
            },
            "highest_rank": {
                "old": False,
                "tier": 19,
                "patched_tier": "Diamond 2",
                "season": "e10a5",
            },
            "by_season": {},
        },
    }


@pytest.mark.asyncio
@respx.mock
async def test_henrik_can_be_configured_without_api_key(monkeypatch):
    monkeypatch.delenv("HENRIK_API_KEY", raising=False)
    monkeypatch.delenv("HENRIK_BASE_URL", raising=False)
    try:
        config = HenrikConfig(_env_file=None)
    except ValidationError:
        pytest.fail("Henrik configuration must allow a missing API key")
    assert config.api_key is None
    assert config.base_url == "https://api.henrikdev.xyz/valorant/v1"
    provider = HenrikProvider(config)
    route = respx.get("https://api.henrikdev.xyz/valorant/v1/status/eu").respond(200)
    try:
        health = await provider.health_check()
        assert health.status == ProviderStatus.HEALTHY
        assert "Authorization" not in route.calls.last.request.headers
        assert "X-API-Key" not in route.calls.last.request.headers
    finally:
        await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_health_check_success(henrik_provider):
    route = respx.get("https://api.henrikdev.xyz/valorant/v1/status/eu").mock(
        return_value=httpx.Response(200)
    )
    health = await henrik_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    assert health.latency_ms is not None and health.latency_ms >= 0
    assert route.calls.last.request.headers["Authorization"] == "test-henrik-key"
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_health_region_and_settings_use_env_prefix(monkeypatch):
    monkeypatch.setenv("HENRIK_API_KEY", "env-key")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://mirror.example/valorant/v1")
    monkeypatch.setenv("HENRIK_HEALTH_REGION", "na")
    monkeypatch.setenv("HENRIK_TIMEOUT", "2.5")
    config = HenrikConfig(retries=0, _env_file=None)
    assert config.api_key == "env-key"
    assert config.timeout == 2.5
    route = respx.get("https://mirror.example/valorant/v1/status/na").respond(200)
    provider = HenrikProvider(config)
    try:
        health = await provider.health_check()
        assert health.status == ProviderStatus.HEALTHY
        assert route.calls.last.request.headers["Authorization"] == "env-key"
    finally:
        await provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("status_code", [401, 429, 503])
async def test_henrik_health_does_not_expose_error_body_or_key(
    henrik_provider, status_code
):
    respx.get("https://api.henrikdev.xyz/valorant/v1/status/eu").respond(
        status_code, text="sensitive-body test-henrik-key"
    )
    health = await henrik_provider.health_check()
    assert health.status == ProviderStatus.UNHEALTHY
    assert "sensitive-body" not in health.model_dump_json()
    assert "test-henrik-key" not in health.model_dump_json()
    assert str(status_code) in health.message
    assert health.latency_ms is not None and health.latency_ms >= 0
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_get_account_success(henrik_provider, account_response):
    route = respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(200, json=account_response)
    )

    player = await henrik_provider.get_account("Player", "123")
    assert player.name == "Player"
    assert player.puuid == "test-puuid"
    request = route.calls.last.request
    assert request.headers.get("Authorization") == "test-henrik-key"
    assert "X-API-Key" not in request.headers
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("wire_format", ["lifetime", "stored"])
async def test_henrik_get_matches_success(henrik_provider, lifetime_match, wire_format):
    if wire_format == "stored":
        metadata = lifetime_match.pop("metadata")
        metadata["started_at"] = metadata.pop("time")
        lifetime_match["meta"] = metadata
    mock_data = {
        "status": 200,
        "data": [lifetime_match],
    }
    route = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Player/123"
    ).mock(return_value=httpx.Response(200, json=mock_data))

    matches = await henrik_provider.get_matches("eu", "Player", "123")
    assert len(matches) == 1
    match = matches[0]
    assert match.metadata.id == "match-uuid"
    assert match.metadata.map.name == "Ascent"
    assert match.metadata.map.id == "map-uuid"
    assert match.metadata.mode == "Competitive"
    assert match.metadata.time == "2026-07-10T12:34:56Z"
    assert (match.stats.kills, match.stats.deaths, match.stats.assists) == (20, 15, 5)
    assert match.stats.score == 250
    assert match.stats.character.name == "Jett"
    assert match.stats.character.id == "agent-uuid"
    assert match.stats.team == "Blue"
    assert (match.teams.red, match.teams.blue) == (13, 9)
    assert route.calls.last.request.headers["Authorization"] == "test-henrik-key"
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_get_rank_uses_v2_and_real_rr(henrik_provider, mmr_response):
    route = respx.get(
        "https://api.henrikdev.xyz/valorant/v2/mmr/eu/Player/123"
    ).respond(200, json=mmr_response)
    get_rank = getattr(henrik_provider, "get_rank", None)
    assert callable(get_rank), "HenrikProvider must provide get_rank"
    rank = await get_rank("eu", "Player", "123")
    assert rank.tier_name == "Diamond 2"
    assert rank.rank_icon_url == "https://example.com/diamond-small.png"
    assert rank.points == 67
    assert route.calls.last.request.headers["Authorization"] == "test-henrik-key"
    assert "X-API-Key" not in route.calls.last.request.headers
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("images", ["missing", None, {}, {"small": None}])
async def test_henrik_get_rank_allows_missing_icon(
    henrik_provider, mmr_response, images
):
    current = mmr_response["data"]["current_data"]
    current["ranking_in_tier"] = 0
    if images == "missing":
        current.pop("images")
    else:
        current["images"] = images
    respx.get("https://api.henrikdev.xyz/valorant/v2/mmr/eu/Player/123").respond(
        200, json=mmr_response
    )
    rank = await henrik_provider.get_rank("eu", "Player", "123")
    assert rank.tier_name == "Diamond 2"
    assert rank.points == 0
    assert rank.rank_icon_url is None
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("images", [[], 17, False])
async def test_henrik_rejects_malformed_rank_images(
    henrik_provider, mmr_response, images
):
    mmr_response["data"]["current_data"]["images"] = images
    respx.get("https://api.henrikdev.xyz/valorant/v2/mmr/eu/Player/123").respond(
        200, json=mmr_response
    )
    with pytest.raises(HenrikError):
        await henrik_provider.get_rank("eu", "Player", "123")
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method", "prefix"),
    [
        ("get_account", "/valorant/v1/account/"),
        ("get_matches", "/valorant/v1/stored-matches/eu%2F%20%3F%23%25/"),
        ("get_rank", "/valorant/v2/mmr/eu%2F%20%3F%23%25/"),
    ],
)
async def test_henrik_escapes_each_url_segment_and_preserves_custom_base(
    henrik_provider, account_response, lifetime_match, mmr_response, method, prefix
):
    henrik_provider.config.base_url = "https://mirror.example/valorant/v1"
    name = "J\u00f6hn /?#%2F+"
    tag = "EU/#+ ?%25"
    expected_path = prefix + "J%C3%B6hn%20%2F%3F%23%252F%2B/EU%2F%23%2B%20%3F%2525"
    payload = {
        "get_account": account_response,
        "get_matches": {"status": 200, "data": [lifetime_match]},
        "get_rank": mmr_response,
    }[method]
    route = respx.get("https://mirror.example" + expected_path).respond(
        200, json=payload
    )
    args = (name, tag) if method == "get_account" else ("eu/ ?#%", name, tag)
    result = await getattr(henrik_provider, method)(*args)
    assert result is not None
    request = route.calls.last.request
    assert request.url.raw_path == expected_path.encode("ascii")
    assert request.url.query == b""
    assert request.headers["Authorization"] == "test-henrik-key"
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_escapes_health_region(henrik_provider):
    henrik_provider.config.health_region = "eu/ ?#%"
    route = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/status/eu%2F%20%3F%23%25"
    ).respond(200)
    health = await henrik_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    assert route.calls.last.request.url.raw_path == (
        b"/valorant/v1/status/eu%2F%20%3F%23%25"
    )
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get_account", "/v1/account/Player/123"),
        ("get_matches", "/v1/stored-matches/eu/Player/123"),
        ("get_rank", "/v2/mmr/eu/Player/123"),
    ],
)
@pytest.mark.parametrize(
    "defect", ["missing-status", "wrong-status", "missing-data", "null-data"]
)
async def test_henrik_rejects_malformed_envelopes(
    henrik_provider,
    account_response,
    lifetime_match,
    mmr_response,
    method,
    path,
    defect,
):
    payload = {
        "get_account": account_response,
        "get_matches": {"status": 200, "data": [lifetime_match]},
        "get_rank": mmr_response,
    }[method]
    payload["diagnostic"] = "sensitive-payload test-henrik-key"
    if defect == "missing-status":
        payload.pop("status")
    elif defect == "wrong-status":
        payload["status"] = 404
    elif defect == "missing-data":
        payload.pop("data")
    else:
        payload["data"] = None
    respx.get("https://api.henrikdev.xyz/valorant" + path).respond(200, json=payload)
    args = ("Player", "123") if method == "get_account" else ("eu", "Player", "123")
    with pytest.raises(HenrikError) as exc:
        await getattr(henrik_provider, method)(*args)
    assert "sensitive-payload" not in str(exc.value)
    assert "test-henrik-key" not in str(exc.value)
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("bad_value", [True, "12"])
@pytest.mark.parametrize(
    ("method", "path", "field"),
    [
        ("get_account", "/v1/account/Player/123", ("data", "account_level")),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "stats", "kills"),
        ),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "stats", "deaths"),
        ),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "stats", "assists"),
        ),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "stats", "score"),
        ),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "teams", "red"),
        ),
        (
            "get_matches",
            "/v1/stored-matches/eu/Player/123",
            ("data", 0, "teams", "blue"),
        ),
        (
            "get_rank",
            "/v2/mmr/eu/Player/123",
            ("data", "current_data", "ranking_in_tier"),
        ),
    ],
)
async def test_henrik_does_not_coerce_malformed_numbers(
    henrik_provider,
    account_response,
    lifetime_match,
    mmr_response,
    method,
    path,
    field,
    bad_value,
):
    payload = {
        "get_account": account_response,
        "get_matches": {"status": 200, "data": [lifetime_match]},
        "get_rank": mmr_response,
    }[method]
    target = payload
    for segment in field[:-1]:
        target = target[segment]
    target[field[-1]] = bad_value
    respx.get("https://api.henrikdev.xyz/valorant" + path).respond(200, json=payload)
    args = ("Player", "123") if method == "get_account" else ("eu", "Player", "123")
    with pytest.raises(HenrikError):
        await getattr(henrik_provider, method)(*args)
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "timestamp", ["not-a-timestamp", "1783686896", "2026-07-10T12:34:56"]
)
async def test_henrik_rejects_invalid_or_ambiguous_match_time(
    henrik_provider, lifetime_match, timestamp
):
    lifetime_match["metadata"]["time"] = timestamp
    respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Player/123"
    ).respond(200, json={"status": 200, "data": [lifetime_match]})
    with pytest.raises(HenrikError):
        await henrik_provider.get_matches("eu", "Player", "123")
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get_account", "/v1/account/Player/123"),
        ("get_matches", "/v1/stored-matches/eu/Player/123"),
        ("get_rank", "/v2/mmr/eu/Player/123"),
    ],
)
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, HenrikAuthenticationError),
        (403, HenrikAuthenticationError),
        (404, HenrikNotFoundError),
        (429, HenrikRateLimitError),
        (500, HenrikError),
    ],
)
async def test_henrik_preserves_http_status_without_exposing_response(
    henrik_provider, method, path, status_code, error_type
):
    respx.get("https://api.henrikdev.xyz/valorant" + path).respond(
        status_code, text="sensitive-body test-henrik-key"
    )
    args = ("Player", "123") if method == "get_account" else ("eu", "Player", "123")
    with pytest.raises(error_type) as exc:
        await getattr(henrik_provider, method)(*args)
    assert type(exc.value) is error_type
    assert getattr(exc.value, "status_code", None) == status_code
    assert "sensitive-body" not in str(exc.value)
    assert "test-henrik-key" not in str(exc.value)
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("body", ["null", "[]", "<html>upstream unavailable</html>"])
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get_account", "/v1/account/Player/123"),
        ("get_matches", "/v1/stored-matches/eu/Player/123"),
        ("get_rank", "/v2/mmr/eu/Player/123"),
    ],
)
async def test_henrik_rejects_invalid_json_or_non_object_response(
    henrik_provider, method, path, body
):
    respx.get("https://api.henrikdev.xyz/valorant" + path).respond(200, text=body)
    args = ("Player", "123") if method == "get_account" else ("eu", "Player", "123")
    with pytest.raises(HenrikError):
        await getattr(henrik_provider, method)(*args)
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_allows_empty_stored_history(henrik_provider):
    respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Player/123"
    ).respond(200, json={"status": 200, "data": []})
    assert await henrik_provider.get_matches("eu", "Player", "123") == []
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_preserves_zero_stats_and_iso_timezone(
    henrik_provider, lifetime_match
):
    lifetime_match["metadata"]["time"] = "2026-07-10T14:34:56+02:00"
    lifetime_match["stats"].update(kills=0, deaths=0, assists=0, score=0)
    lifetime_match["teams"] = {"red": 0, "blue": 0}
    respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Player/123"
    ).respond(200, json={"status": 200, "data": [lifetime_match]})
    matches = await henrik_provider.get_matches("eu", "Player", "123")
    assert len(matches) == 1
    match = matches[0]
    assert match.metadata.time == "2026-07-10T14:34:56+02:00"
    assert (match.stats.kills, match.stats.deaths, match.stats.assists) == (0, 0, 0)
    assert match.stats.score == 0
    assert (match.teams.red, match.teams.blue) == (0, 0)
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError])
async def test_henrik_health_handles_transport_failures(henrik_provider, error_type):
    respx.get("https://api.henrikdev.xyz/valorant/v1/status/eu").mock(
        side_effect=error_type("sensitive-transport test-henrik-key")
    )
    health = await henrik_provider.health_check()
    assert health.status == ProviderStatus.UNHEALTHY
    assert "sensitive-transport" not in health.model_dump_json()
    assert "test-henrik-key" not in health.model_dump_json()
    assert health.latency_ms is not None and health.latency_ms >= 0
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_not_found(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/NonExistent/000").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(HenrikNotFoundError) as exc:
        await henrik_provider.get_account("NonExistent", "000")
    assert exc.value.status_code == 404
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_auth_failed(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(HenrikAuthenticationError) as exc:
        await henrik_provider.get_account("Player", "123")
    assert exc.value.status_code == 401
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_rate_limit(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(HenrikRateLimitError) as exc:
        await henrik_provider.get_account("Player", "123")
    assert exc.value.status_code == 429
    await henrik_provider.close()
