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
