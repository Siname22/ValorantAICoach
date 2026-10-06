import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

ENTRYPOINT = APP_DIR / "app.py"


@pytest.fixture
def coach_page(monkeypatch):
    from components import sections

    monkeypatch.setattr(sections, "is_configured", lambda: True)
    return AppTest.from_file(str(ENTRYPOINT), default_timeout=10)


def test_ai_coach_without_player_context_uses_default_prompt(coach_page, monkeypatch):
    from components import sections

    captured_prompt = []

    def mock_get_client(prompt):
        captured_prompt.append(prompt)
        client = SimpleNamespace(
            send_message=Mock(return_value="Coach advice without player context."),
            close=Mock(),
            model="gemini-2.5-flash",
            active_model="gemini-2.5-flash",
        )
        return client

    monkeypatch.setattr(sections, "get_gemini_client", mock_get_client)

    coach_page.run().switch_page("pages/6_AI_Coach.py").run()
    coach_page.chat_input[0].set_value("How to play Haven?").run()

    assert not coach_page.exception
    assert len(captured_prompt) == 1
    assert "Contexto del jugador" not in captured_prompt[0]
    assert "Actualmente no tienes estadísticas en vivo" in captured_prompt[0]


def test_ai_coach_with_player_context_injects_stats_and_matches(
    coach_page, monkeypatch
):
    from components import sections

    captured_prompt = []

    def mock_get_client(prompt):
        captured_prompt.append(prompt)
        client = SimpleNamespace(
            send_message=Mock(return_value="Personalized coach advice for Jett."),
            close=Mock(),
            model="gemini-2.5-flash",
            active_model="gemini-2.5-flash",
        )
        return client

    monkeypatch.setattr(sections, "get_gemini_client", mock_get_client)

    coach_page.run()
    # Inject search result into session state
    coach_page.session_state["player_search_result"] = {
        "game_name": "TenZ",
        "tag_line": "001",
        "error": None,
        "profile": {
            "game_name": "TenZ",
            "tag_line": "001",
            "region": "na",
            "account_level": 150,
        },
        "rank": {"tier_name": "Radiant", "rank_name": "Radiant", "points": 450},
        "matches_payload": {
            "matches": [
                {
                    "map_name": "Ascent",
                    "agent_name": "Jett",
                    "result": "Victory",
                    "kills": 25,
                    "deaths": 12,
                    "assists": 6,
                }
            ]
        },
    }

    coach_page.switch_page("pages/6_AI_Coach.py").run()
    # Verify that active player badge is displayed in markdown
    assert any("TenZ#001" in item.value for item in coach_page.markdown)
    assert any("Radiant" in item.value for item in coach_page.markdown)

    coach_page.chat_input[0].set_value("How can I improve my entry?").run()

    assert not coach_page.exception
    assert len(captured_prompt) == 1
    assert "Contexto del jugador" in captured_prompt[0]
    assert "TenZ" in captured_prompt[0]
    assert "Radiant" in captured_prompt[0]
    assert "Ascent" in captured_prompt[0]
    assert "Jett" in captured_prompt[0]
