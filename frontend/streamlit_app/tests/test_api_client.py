from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import requests

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from utils.api_client import APIClient, APIClientError  # noqa: E402

BASE_URL = "https://api.example.invalid"
PRIVATE_DETAIL = "private-token internal-host <script>secret</script>"


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected external HTTP request")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


def response(status: int, body: str) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result.encoding = "utf-8"
    result._content = body.encode("utf-8")
    return result


@pytest.mark.parametrize(
    "error_type",
    [requests.ConnectionError, requests.Timeout, requests.RequestException],
)
def test_request_failures_become_sanitized_client_errors(monkeypatch, error_type):
    def fail(*args, **kwargs):
        raise error_type(PRIVATE_DETAIL)

    monkeypatch.setattr(requests, "get", fail)

    with pytest.raises(APIClientError) as caught:
        APIClient(BASE_URL).get_player_profile("Player", "EU1")

    assert str(caught.value)
    assert "private-token" not in str(caught.value)
    assert "internal-host" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("body", ["not json", "[]", "null", "42", '"secret"'])
def test_success_requires_a_json_object(monkeypatch, body):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response(200, body))

    with pytest.raises(APIClientError) as caught:
        APIClient(BASE_URL).get_health()

    assert "not json" not in str(caught.value)
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("status", [404, 503])
@pytest.mark.parametrize(
    "body",
    [
        PRIVATE_DETAIL,
        json.dumps({"detail": PRIVATE_DETAIL}),
        json.dumps({"detail": [{"input": PRIVATE_DETAIL}]}),
        json.dumps([PRIVATE_DETAIL]),
        "null",
    ],
)
def test_http_errors_do_not_expose_response_bodies(monkeypatch, status, body):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response(status, body))

    with pytest.raises(APIClientError) as caught:
        APIClient(BASE_URL).get_player_profile("Player", "EU1")

    assert str(status) in str(caught.value)
    for private_text in ("private-token", "internal-host", "<script>", "input"):
        assert private_text not in str(caught.value)


@pytest.mark.parametrize(
    ("method_name", "suffix"),
    [
        ("get_player_profile", ""),
        ("get_player_rank", "/rank"),
        ("get_player_matches", "/matches"),
    ],
)
def test_identity_segments_are_explicitly_encoded(monkeypatch, method_name, suffix):
    calls = []

    def get(url, *, timeout):
        calls.append((url, timeout))
        payloads = {
            "": {"game_name": "Player", "tag_line": "EU1"},
            "/rank": {"tier_name": "Gold 1", "points": 0},
            "/matches": {"matches": [], "count": 0},
        }
        return response(200, json.dumps(payloads[suffix]))

    monkeypatch.setattr(requests, "get", get)
    getattr(APIClient(BASE_URL + "/"), method_name)("A/B?#%20 \u00e9", "T/%?# +")

    assert calls == [
        (
            BASE_URL
            + "/players/A%2FB%3F%23%2520%20%C3%A9/T%2F%25%3F%23%20%2B"
            + suffix,
            10.0,
        )
    ]


@pytest.mark.parametrize(
    ("method_name", "args", "payload"),
    [
        ("get_health", (), {"status": "ok", "version": "0.4.0"}),
        (
            "get_player_profile",
            ("Player", "EU1"),
            {"game_name": "Player", "tag_line": "EU1", "region": "eu"},
        ),
        (
            "get_player_rank",
            ("Player", "EU1"),
            {"tier_name": "Gold 1", "rank_name": None, "points": 0},
        ),
        ("get_player_matches", ("Player", "EU1"), {"matches": [], "count": 0}),
    ],
)
def test_flat_backend_objects_are_preserved(monkeypatch, method_name, args, payload):
    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: response(200, json.dumps(payload))
    )

    assert getattr(APIClient(BASE_URL), method_name)(*args) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"matches": None},
        {"matches": {}},
        {"matches": ["private body"]},
        {"matches": [{}]},
        {"matches": [{"map_name": "Ascent"}]},
    ],
)
def test_malformed_history_is_unavailable_not_empty_or_renderable(monkeypatch, payload):
    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: response(200, json.dumps(payload))
    )
    with pytest.raises(APIClientError) as error:
        APIClient(BASE_URL).get_player_matches("Player", "EU1")
    assert "private body" not in str(error.value)


@pytest.mark.parametrize("method_name", ["get_player_profile", "get_player_rank"])
def test_empty_player_data_is_not_presented_as_a_confirmed_player(
    monkeypatch, method_name
):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response(200, "{}"))
    with pytest.raises(APIClientError):
        getattr(APIClient(BASE_URL), method_name)("Player", "EU1")


def test_api_client_coaching_reports(monkeypatch):
    client = APIClient(BASE_URL)
    report_data = {
        "id": "rep-123",
        "payload": {"title": "Report"},
        "evidence": [],
    }

    # Test POST generate
    monkeypatch.setattr(
        requests, "post", lambda *a, **kw: response(200, json.dumps(report_data))
    )
    generated = client.generate_coaching_report("Player", "EU1", limit=3)
    assert generated["id"] == "rep-123"

    # Test GET list
    list_data = {"reports": [report_data], "count": 1}
    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: response(200, json.dumps(list_data))
    )
    listed = client.list_coaching_reports("Player", "EU1", limit=5)
    assert listed["count"] == 1

    # Test GET detail
    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: response(200, json.dumps(report_data))
    )
    detail = client.get_coaching_report("Player", "EU1", "rep-123")
    assert detail["id"] == "rep-123"


def test_api_client_player_stats(monkeypatch):
    client = APIClient(BASE_URL)
    stats_data = {
        "kd_ratio": 1.25,
        "win_pct": 55.0,
        "headshot_pct": 24.5,
        "matches_played": 10,
        "damage_per_round": 145.2,
        "source": "calculated",
    }
    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: response(200, json.dumps(stats_data))
    )
    result = client.get_player_stats("Player", "EU1")
    assert result["kd_ratio"] == 1.25

    monkeypatch.setattr(requests, "get", lambda *a, **kw: response(200, "[]"))
    with pytest.raises(APIClientError):
        client.get_player_stats("Player", "EU1")


def test_api_client_auth_and_account_linking(monkeypatch):
    client = APIClient(BASE_URL)

    # Register
    monkeypatch.setattr(
        requests,
        "post",
        lambda *a, **kw: response(
            201,
            json.dumps(
                {
                    "id": "u1",
                    "email": "test@example.com",
                    "is_active": True,
                    "created_at": "2026-10-07T12:00:00Z",
                }
            ),
        ),
    )
    user = client.register("test@example.com", "Password123!")
    assert user["id"] == "u1"

    # Login
    monkeypatch.setattr(
        requests,
        "post",
        lambda *a, **kw: response(
            200,
            json.dumps({"access_token": "mock.jwt.token", "token_type": "bearer"}),
        ),
    )
    token_resp = client.login("test@example.com", "Password123!")
    assert token_resp["access_token"] == "mock.jwt.token"
    assert client.token == "mock.jwt.token"

    # Get me
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **kw: response(
            200,
            json.dumps(
                {
                    "id": "u1",
                    "email": "test@example.com",
                    "is_active": True,
                    "created_at": "2026-10-07T12:00:00Z",
                }
            ),
        ),
    )
    me = client.get_me()
    assert me["email"] == "test@example.com"

    # Link account
    monkeypatch.setattr(
        requests,
        "post",
        lambda *a, **kw: response(
            201,
            json.dumps(
                {
                    "id": "acc-1",
                    "user_id": "u1",
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                    "puuid": None,
                    "region": "na",
                    "is_primary": True,
                    "linked_at": "2026-10-07T12:00:00Z",
                }
            ),
        ),
    )
    acc = client.link_account("TenZ", "SEN", region="na", is_primary=True)
    assert acc["game_name"] == "TenZ"
    assert acc["is_primary"] is True

    # List linked accounts
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **kw: response(200, json.dumps([acc])),
    )
    accounts = client.list_linked_accounts()
    assert len(accounts) == 1
    assert accounts[0]["id"] == "acc-1"

    # Delete linked account
    monkeypatch.setattr(
        requests,
        "delete",
        lambda *a, **kw: response(
            200, json.dumps({"status": "deleted", "account_id": "acc-1"})
        ),
    )
    del_res = client.delete_linked_account("acc-1")
    assert del_res["status"] == "deleted"

    # Invalidate cache
    monkeypatch.setattr(
        requests,
        "delete",
        lambda *a, **kw: response(
            200, json.dumps({"status": "ok", "invalidated_snapshots": 2})
        ),
    )
    cache_res = client.invalidate_cache("TenZ", "SEN")
    assert cache_res["status"] == "ok"

    # Get progression
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **kw: response(
            200,
            json.dumps(
                {
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                    "total_matches_analyzed": 5,
                    "total_reports_generated": 2,
                    "kd_metric": {"trend": "improving", "current": 1.4},
                    "resolved_focus_areas": ["Aim"],
                    "active_focus_areas": ["Positioning"],
                }
            ),
        ),
    )
    prog = client.get_player_progression("TenZ", "SEN")
    assert prog["game_name"] == "TenZ"
    assert prog["kd_metric"]["trend"] == "improving"

    # Sync player
    monkeypatch.setattr(
        requests,
        "post",
        lambda *a, **kw: response(
            200,
            json.dumps(
                {
                    "synced": True,
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                    "new_report_generated": True,
                    "report_id": "rep-123",
                    "matches_synced": 5,
                    "synced_at": "2026-10-08T10:00:00Z",
                }
            ),
        ),
    )
    sync_res = client.sync_player("TenZ", "SEN", region="na")
    assert sync_res["synced"] is True
    assert sync_res["report_id"] == "rep-123"

    # Analyze scoreboard
    monkeypatch.setattr(
        requests,
        "post",
        lambda *a, **kw: response(
            200,
            json.dumps(
                {
                    "match_id": "vision-123",
                    "map_name": "Ascent",
                    "game_mode": "Competitive",
                    "result": "Victory",
                    "rounds_won": 13,
                    "rounds_lost": 8,
                    "confidence_score": 0.95,
                    "extractor_engine": "heuristic-ocr",
                    "tactical_takeaways": ["Great round conversions."],
                    "persisted_as_match": True,
                }
            ),
        ),
    )
    analysis = client.analyze_scoreboard(
        "synthetic-base64",
        game_name="TenZ",
        tag_line="SEN",
        save_to_history=True,
    )
    assert analysis["match_id"] == "vision-123"
    assert analysis["map_name"] == "Ascent"
    assert analysis["persisted_as_match"] is True
