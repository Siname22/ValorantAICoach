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


# Invalid avatar references must not be passed to Streamlit's file/image loader.
@pytest.mark.parametrize(
    "avatar",
    [
        pytest.param("avatar.png", id="relative-path"),
        pytest.param("/tmp/avatar.png", id="absolute-path"),
        pytest.param(r"C:\private\avatar.png", id="windows-path"),
        pytest.param(r"\\server\share\avatar.png", id="unc-path"),
        pytest.param("file:///tmp/avatar.png", id="file-url"),
        pytest.param("//cdn.example.test/avatar.png", id="scheme-relative"),
        pytest.param("data:image/png;base64,aGVsbG8=", id="data-url"),
        pytest.param("http://cdn.example.test/avatar.png", id="http"),
        pytest.param("https://user:password@cdn.example.test/a.png", id="credentials"),
        pytest.param("https://@cdn.example.test/a.png", id="empty-credentials"),
        pytest.param("https:///avatar.png", id="missing-host"),
        pytest.param("https://[bad-address]/a.png", id="bad-ipv6"),
        pytest.param("https://cdn.example.test:bad/a.png", id="bad-port"),
        pytest.param("https://cdn.example.test:65536/a.png", id="port-range"),
        pytest.param("https://cdn..example.test/a.png", id="empty-host-label"),
        pytest.param("https://-cdn.example.test/a.png", id="bad-host-label"),
        pytest.param("https://cdn%2eexample.test/a.png", id="encoded-host"),
        pytest.param("https://localhost/a.png", id="local-host"),
        pytest.param("https://127.0.0.1/a.png", id="loopback"),
        pytest.param("https://[::1]/a.png", id="ipv6-loopback"),
        pytest.param("https://127.1/a.png", id="short_ip"),
        pytest.param("https://127.0.0.0x1/a.png", id="alternate-loopback"),
        pytest.param("https://10.0.0.0x1/a.png", id="alternate-private"),
        pytest.param("https://169.254.169.0xfe/a.png", id="alternate-link-local"),
        pytest.param("https://127.0.0.0X01/a.png", id="alternate-uppercase"),
        pytest.param("https://127.0.0.0x/a.png", id="alternate-empty-hex"),
        pytest.param("https://[2606:4700:4700::1111%25eth0]/a.png", id="scoped_ip"),
        pytest.param("https://cdn.example.test\\avatar.png", id="backslash"),
        pytest.param(" https://cdn.example.test/a.png", id="leading-space"),
        pytest.param("https://cdn.example.test/a b.png", id="raw-space"),
        pytest.param("https://cdn.example.test/a\n.png", id="newline"),
        pytest.param("https://cdn.example.test/a\x00.png", id="nul"),
        pytest.param("https://cdn.example.test/a\x7f.png", id="del"),
        pytest.param("https://cdn.example.test/a\x85.png", id="unicode-control"),
        pytest.param("https://cdn.example.test/a%0a.png", id="encoded-control"),
        pytest.param(True, id="boolean"),
        pytest.param(["https://cdn.example.test/a.png"], id="list"),
    ],
)
def test_rejected_avatars_keep_profile_rank_and_matches(player_app, avatar):
    app, payloads, calls = player_app
    payloads["profile"]["avatar_url"] = avatar
    submit(app)

    assert not app.get("image")
    assert "Avatar placeholder" in markdown(app)
    assert "TestPlayer#NA1" in markdown(app)
    assert "<strong>Level:</strong> 42" in markdown(app)
    assert "<strong>Region:</strong> na" in markdown(app)
    assert "Gold 1" in markdown(app)
    assert app.dataframe[0].value.iloc[0]["map_name"] == "Ascent"
    assert [endpoint for endpoint, _ in calls] == ["profile", "rank", "matches"]
    app.run()
    assert not app.exception
    assert not app.get("image")
    assert "TestPlayer#NA1" in markdown(app)
    assert len(calls) == 3


# Valid HTTPS references must render as URLs, without server-side image fetching.
@pytest.mark.parametrize(
    "avatar",
    [
        "https://cdn.example.test/avatar.png",
        "https://cdn.example.test:8443/avatar%20one.png?v=2#crop",
        "HTTPS://cdn.example.test/avatar.png",
        "https://[2606:4700:4700::1111]/avatar.png",
        "https://xn--bcher-kva.example/avatar.png",
        pytest.param("https://8.8.8.8/avatar.png", id="public_ipv4"),
    ],
)
def test_valid_https_avatars_render_without_extra_requests(player_app, avatar):
    app, payloads, calls = player_app
    payloads["profile"]["avatar_url"] = avatar
    submit(app)

    assert len(app.get("image")) == 1
    assert app.get("image")[0].proto.imgs[0].url == avatar
    assert "Avatar placeholder" not in markdown(app)
    assert "TestPlayer#NA1" in markdown(app)
    assert len(calls) == 3
    app.run()
    assert not app.exception
    assert app.get("image")[0].proto.imgs[0].url == avatar
    assert len(calls) == 3


def test_player_search_generates_and_displays_coaching_report(player_app, monkeypatch):
    app, payloads, calls = player_app
    submit(app)

    report_payload = {
        "id": "rep-test-1",
        "payload": {
            "title": "Tactical Coaching: TestPlayer#NA1",
            "executive_summary": "Solid mechanics, need economy discipline.",
            "key_strengths": ["High first blood conversion"],
            "critical_flaws": ["Forcing after round 2 losses"],
            "training_plan": [
                "Practice save rounds on eco",
                "Warmup 15 mins in Deathmatch",
            ],
            "evidence": [{"metric": "ACS", "value": 240}],
        },
    }

    def post(url, *args, **kwargs):
        res = requests.Response()
        res.status_code = 200
        res.encoding = "utf-8"
        res._content = json.dumps(report_payload).encode("utf-8")
        return res

    monkeypatch.setattr(requests, "post", post)

    gen_btn = next((b for b in app.button if "Generate" in b.label), None)
    assert gen_btn is not None
    gen_btn.click().run()
    assert not app.exception

    text = markdown(app)
    assert "Tactical Coaching: TestPlayer#NA1" in text
    assert any("Solid mechanics" in item.value for item in app.info)
    assert "High first blood conversion" in text
    assert "Forcing after round 2 losses" in text
    assert "Step 1:" in text
