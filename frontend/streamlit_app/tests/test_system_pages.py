import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from streamlit.testing.v1 import AppTest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def page(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps({"status": "degraded", "providers": {}}).encode()
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setenv(
        "VALORANT_API_BASE_URL", "https://configured-api.example.test/v1"
    )
    return AppTest.from_file(str(ENTRYPOINT), default_timeout=10)


def test_first_screen_is_player_lookup(page):
    page.run()
    assert not page.exception
    assert [item.label for item in page.text_input] == ["Game name", "Tag line"]
    assert page.button[0].label == "Search player"


def test_api_docs_use_configured_backend(page):
    page.run().switch_page("pages/5_API_Docs.py").run()
    assert not page.exception
    urls = [item.proto.url for item in page.get("link_button")]
    assert "https://configured-api.example.test/v1/docs" in urls
    assert "https://configured-api.example.test/v1/redoc" in urls
    markdown = "\n".join(item.value for item in page.markdown)
    assert "/overview" in markdown
    assert "/stats" in markdown


def test_roadmap_reports_milestones_not_invented_percentages(page):
    page.run().switch_page("pages/4_Roadmap.py").run()
    assert not page.exception
    assert not page.get("plotly_chart")
    assert len(page.dataframe) == 1
    rows = page.dataframe[0].value
    assert {"Milestone", "Status", "Target"} <= set(rows.columns)
    ocr = rows.loc[rows["Milestone"] == "OCR and tactical timeline"].iloc[0]
    assert ocr["Status"] == "Not implemented"
    assert ocr["Target"] == "2026-11-20"


def test_coach_last_handler_does_not_log_private_exception(page, monkeypatch, caplog):
    from components import sections

    def fail(*args, **kwargs):
        raise RuntimeError("private conversation body and token")

    monkeypatch.setattr(sections, "is_configured", lambda: True)
    monkeypatch.setattr(sections, "get_gemini_client", fail)
    page.run().switch_page("pages/6_AI_Coach.py").run()
    page.chat_input[0].set_value("test question").run()
    assert not page.exception
    assert page.error
    assert "private conversation body and token" not in caplog.text
    assert "private conversation" not in page.error[0].value


@pytest.mark.parametrize("failed", [False, True])
def test_coach_releases_client_on_success_and_failure(page, monkeypatch, failed):
    from components import sections
    from utils.gemini_client import GeminiClientError

    client = SimpleNamespace(
        send_message=Mock(
            return_value="Reply",
            side_effect=GeminiClientError("Unavailable") if failed else None,
        ),
        close=Mock(),
        model="test",
        active_model="test",
    )
    monkeypatch.setattr(sections, "is_configured", lambda: True)
    monkeypatch.setattr(sections, "get_gemini_client", lambda *args, **kwargs: client)
    page.run().switch_page("pages/6_AI_Coach.py").run()
    page.chat_input[0].set_value("test question").run()
    assert not page.exception
    assert bool(page.error) is failed
    client.close.assert_called_once()
