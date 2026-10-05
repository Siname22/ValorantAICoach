from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def player_app(monkeypatch):
    payloads = {
        "profile": {
            "puuid": "player-id",
            "game_name": "TestPlayer",
            "tag_line": "NA1",
            "region": "na",
            "account_level": 42,
            "avatar_url": None,
            "rank_name": None,
            "rank_tier": None,
            "rank_icon_url": None,
        },
        "rank": {
            "tier_name": "Gold 1",
            "rank_name": "Gold",
            "rank_icon_url": None,
            "points": 0,
        },
        "matches": {
            "matches": [
                {
                    "match_id": "match-id",
                    "map_name": "Ascent",
                    "mode": "Competitive",
                    "timestamp": 1234567890,
                    "result": "Victory",
                    "kills": 20,
                    "deaths": 10,
                    "assists": 5,
                    "score": None,
                    "agent_name": "Sage",
                    "provider": "riot",
                    "provider_score": None,
                }
            ],
            "count": 1,
        },
    }
    calls = []

    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected external HTTP request")

    def get(url, *, timeout):
        path = urlsplit(url).path
        endpoint = path.rsplit("/", 1)[-1]
        endpoint = endpoint if endpoint in ("rank", "matches") else "profile"
        calls.append((endpoint, path))
        payload = payloads[endpoint]
        if isinstance(payload, Exception):
            raise payload
        result = requests.Response()
        result.status_code = 200
        result.encoding = "utf-8"
        result._content = json.dumps(payload).encode("utf-8")
        return result

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("VALORANT_API_BASE_URL", "https://api.example.invalid")
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=10).run()
    assert not app.exception, [item.message for item in app.exception]
    app.switch_page("pages/2_Player_Search.py").run()
    assert not app.exception, [item.message for item in app.exception]
    return app, payloads, calls


def submit(app, game_name="TestPlayer", tag_line="NA1"):
    app.text_input[0].set_value(game_name)
    app.text_input[1].set_value(tag_line)
    app.button[0].click().run()
    assert not app.exception, [item.message for item in app.exception]


def markdown(app):
    return "\n".join(item.value for item in app.markdown)


@pytest.mark.parametrize("failed", [("rank",), ("matches",), ("rank", "matches")])
def test_optional_outages_keep_profile_and_other_available_data(player_app, failed):
    app, payloads, calls = player_app
    for endpoint in failed:
        payloads[endpoint] = requests.Timeout("private-token internal-host")

    submit(app)

    assert "TestPlayer#NA1" in markdown(app)
    assert [endpoint for endpoint, _ in calls] == ["profile", "rank", "matches"]
    warnings = "\n".join(item.value for item in app.warning).lower()
    for endpoint in failed:
        assert endpoint in warnings
        assert "unavailable" in warnings
    assert "private-token" not in warnings
    if "rank" not in failed:
        assert "Gold 1" in markdown(app)
    if "matches" not in failed:
        assert app.dataframe[0].value.iloc[0]["map_name"] == "Ascent"
    else:
        assert not app.dataframe
        assert not any("No matches" in item.value for item in app.info)

    app.run()
    assert not app.exception
    assert "TestPlayer#NA1" in markdown(app)
    assert [endpoint for endpoint, _ in calls] == ["profile", "rank", "matches"]
    assert "unavailable" in "\n".join(item.value for item in app.warning).lower()


def test_results_persist_on_reruns_without_refetching(player_app):
    app, _, calls = player_app
    submit(app)
    app.text_input[0].set_value("UnsubmittedPlayer").run()

    assert not app.exception
    assert "TestPlayer#NA1" in markdown(app)
    assert "Gold 1" in markdown(app)
    assert app.dataframe[0].value.iloc[0]["map_name"] == "Ascent"
    assert [endpoint for endpoint, _ in calls] == ["profile", "rank", "matches"]


def test_empty_history_is_distinct_from_an_outage(player_app):
    app, payloads, _ = player_app
    payloads["matches"] = {"matches": [], "count": 0}
    submit(app)
    app.run()

    assert not app.exception
    assert "TestPlayer#NA1" in markdown(app)
    assert any("No matches" in item.value for item in app.info)
    assert not app.warning
    assert not app.dataframe


@pytest.mark.parametrize(
    "payload", [{}, {"matches": [{}]}, {"matches": "private body"}]
)
def test_malformed_history_keeps_identity_and_reports_unavailable(player_app, payload):
    app, payloads, calls = player_app
    payloads["matches"] = payload
    submit(app)
    assert "TestPlayer#NA1" in markdown(app)
    assert "Gold 1" in markdown(app)
    assert any(
        "matches" in item.value and "unavailable" in item.value for item in app.warning
    )
    assert not app.dataframe
    assert not any("No matches" in item.value for item in app.info)
    app.run()
    assert not app.exception
    assert len(calls) == 3


@pytest.mark.parametrize(
    ("game_name", "tag_line"), [(" \t ", "NA1"), ("Player", " \t ")]
)
def test_whitespace_only_identity_is_rejected_without_http(
    player_app, game_name, tag_line
):
    app, _, calls = player_app
    submit(app, game_name, tag_line)

    assert calls == []
    assert any("both a game name and a tag line" in item.value for item in app.warning)
    assert "### Profile" not in markdown(app)


def test_identity_is_trimmed_before_requests(player_app):
    app, _, calls = player_app
    submit(app, " TestPlayer \t", " NA1 ")

    assert calls == [
        ("profile", "/players/TestPlayer/NA1"),
        ("rank", "/players/TestPlayer/NA1/rank"),
        ("matches", "/players/TestPlayer/NA1/matches"),
    ]


def test_zero_ranked_rating_is_displayed(player_app):
    app, _, _ = player_app
    submit(app)

    assert "Points: 0" in markdown(app)


@pytest.mark.parametrize("use_input_fallback", [False, True])
def test_dynamic_player_and_rank_values_are_html_escaped(
    player_app, use_input_fallback
):
    app, payloads, _ = player_app
    if use_input_fallback:
        del payloads["profile"]["game_name"]
        del payloads["profile"]["tag_line"]
    else:
        payloads["profile"]["game_name"] = "<script>player</script>"
        payloads["profile"]["tag_line"] = '<b title="tag">tag</b>'
    payloads["profile"]["region"] = "<img src=x onerror=region>"
    payloads["profile"]["account_level"] = "<b>level</b>"
    payloads["rank"]["tier_name"] = "<script>tier</script>"
    payloads["rank"]["rank_name"] = "<b>rank</b>"
    submit(app, "<script>player</script>", '<b title="tag">tag</b>')

    content = markdown(app)
    assert "&lt;script&gt;player&lt;/script&gt;" in content
    assert "&lt;b title=&quot;tag&quot;&gt;tag&lt;/b&gt;" in content
    assert "&lt;img src=x onerror=region&gt;" in content
    assert "&lt;b&gt;level&lt;/b&gt;" in content
    assert "&lt;script&gt;tier&lt;/script&gt;" in content
    assert "&lt;b&gt;rank&lt;/b&gt;" in content
    assert "<script>" not in content
    assert "<img src=x" not in content


def test_profile_failure_prevents_optional_fetches_and_clears_previous_result(
    player_app,
):
    app, payloads, calls = player_app
    submit(app)
    calls.clear()
    payloads["profile"] = requests.ConnectionError("private-token internal-host")
    submit(app, "OtherPlayer", "EU1")

    assert [endpoint for endpoint, _ in calls] == ["profile"]
    assert app.error
    assert "private-token" not in app.error[0].value
    assert "TestPlayer#NA1" not in markdown(app)
    assert "### Profile" not in markdown(app)
    assert not app.dataframe
    app.run()
    assert not app.exception
    assert "TestPlayer#NA1" not in markdown(app)
