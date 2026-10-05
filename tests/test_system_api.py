import httpx
import pytest
import respx
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def provider_environment(monkeypatch):
    for provider in ("RIOT", "HENRIK", "TRACKER"):
        monkeypatch.setenv(f"{provider}_API_KEY", "")
        monkeypatch.setenv(f"{provider}_ENABLED", "true")
        monkeypatch.setenv(f"{provider}_RETRIES", "0")


@pytest.mark.parametrize(
    "path", ["/players/Test/EU1", "/players/Test/EU1/rank", "/players/Test/EU1/matches"]
)
@respx.mock
def test_missing_keys_return_service_unavailable(provider_environment, path):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path)
    assert response.status_code == 503
    assert not respx.calls


@respx.mock
def test_health_reports_disabled_providers_without_network(provider_environment):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["providers"] == {
        "riot": "disabled",
        "henrik": "disabled",
        "tracker": "disabled",
    }
    assert not respx.calls


@respx.mock
def test_liveness_does_not_depend_on_external_apis(provider_environment):
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert not respx.calls


@respx.mock
def test_single_provider_works_and_clients_close(provider_environment, monkeypatch):
    monkeypatch.setenv("HENRIK_API_KEY", "test-key")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://api.henrikdev.xyz/valorant/v1")
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Test/EU1").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "data": {
                    "puuid": "real-player-id",
                    "name": "Test",
                    "tag": "EU1",
                    "region": "eu",
                    "account_level": 20,
                },
            },
        )
    )
    with TestClient(app) as client:
        response = client.get("/players/Test/EU1")
        assert response.status_code == 200
        assert response.json()["puuid"] == "real-player-id"
        service = getattr(app.state, "player_service", None)
        assert service is not None
        http_client = service.henrik.client._client
        assert not http_client.is_closed
    assert http_client.is_closed


@respx.mock
def test_invalid_provider_config_is_reported_without_leaking_key(
    provider_environment, monkeypatch
):
    monkeypatch.setenv("HENRIK_API_KEY", "private-key-do-not-log")
    monkeypatch.setenv("HENRIK_TIMEOUT", "invalid")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["providers"]["henrik"] == "misconfigured"
    assert "private-key-do-not-log" not in response.text
    assert not respx.calls


@respx.mock
def test_henrik_history_pipeline_preserves_real_player_stats(
    provider_environment, monkeypatch
):
    monkeypatch.setenv("HENRIK_API_KEY", "test-key")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://api.henrikdev.xyz/valorant/v1")
    account = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/account/Test/EU1"
    ).respond(
        200,
        json={
            "status": 200,
            "data": {
                "puuid": "real-player-id",
                "name": "Test",
                "tag": "EU1",
                "region": "eu",
                "account_level": 20,
            },
        },
    )
    matches = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Test/EU1"
    ).respond(
        200,
        json={
            "status": 200,
            "data": [
                {
                    "meta": {
                        "id": "eu-match",
                        "map": {"id": "ascent-id", "name": "Ascent"},
                        "mode": "Competitive",
                        "started_at": "2026-10-04T12:00:00Z",
                    },
                    "stats": {
                        "kills": 24,
                        "deaths": 12,
                        "assists": 7,
                        "score": 300,
                        "team": "Blue",
                        "character": {"id": "jett-id", "name": "Jett"},
                    },
                    "teams": {"red": 7, "blue": 13},
                }
            ],
        },
    )
    with TestClient(app) as client:
        response = client.get("/players/Test/EU1/matches?limit=1")
    assert response.status_code == 200
    assert response.json()["matches"][0] == {
        "match_id": "eu-match",
        "map_name": "Ascent",
        "mode": "Competitive",
        "timestamp": "2026-10-04T12:00:00Z",
        "result": "Victory",
        "kills": 24,
        "deaths": 12,
        "assists": 7,
        "score": None,
        "provider_score": 300,
        "provider": "henrik",
        "agent_name": "Jett",
    }
    assert account.call_count == 1
    assert matches.calls.last.request.headers["Authorization"] == "test-key"


@pytest.mark.parametrize("provider", ["RIOT", "HENRIK", "TRACKER"])
@respx.mock
def test_malformed_upstream_data_returns_502(
    provider_environment, monkeypatch, provider
):
    monkeypatch.setenv(f"{provider}_API_KEY", "test-key")
    monkeypatch.setenv("RIOT_ACCOUNT_BASE_URL", "https://europe.api.riotgames.com")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://api.henrikdev.xyz/valorant/v1")
    monkeypatch.setenv(
        "TRACKER_BASE_URL", "https://public-api.tracker.gg/v2/valorant/standard"
    )
    respx.get(url__regex=r"https://.*").respond(200, json={"private": "upstream-body"})
    with TestClient(app) as client:
        response = client.get("/players/Test/EU1")
    assert response.status_code == 502
    assert "upstream-body" not in response.text


@pytest.mark.parametrize(
    "url", ["http://[broken", "https:tracker.test", " https://tracker.test "]
)
@respx.mock
def test_invalid_provider_url_is_misconfigured(provider_environment, monkeypatch, url):
    monkeypatch.setenv("TRACKER_API_KEY", "test-key")
    monkeypatch.setenv("TRACKER_BASE_URL", url)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.json()["providers"]["tracker"] == "misconfigured"
    assert not respx.calls


@pytest.mark.parametrize(
    ("suffix", "payload"),
    [
        ("", {"data": None}),
        ("", {"data": []}),
        ("/matches", {"data": {"matches": [None]}}),
        ("/matches", {"data": {"matches": [{"metadata": None}]}}),
    ],
)
@respx.mock
def test_tracker_invalid_nested_data_returns_502(
    provider_environment, monkeypatch, suffix, payload
):
    monkeypatch.setenv("TRACKER_API_KEY", "test-key")
    monkeypatch.setenv("TRACKER_BASE_URL", "https://tracker.test")
    respx.get(url__regex=r"https://tracker.test/.*").respond(200, json=payload)
    with TestClient(app) as client:
        response = client.get(f"/players/Test/EU1{suffix}")
    assert response.status_code == 502
