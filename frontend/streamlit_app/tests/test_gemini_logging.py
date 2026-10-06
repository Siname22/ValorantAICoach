import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import gemini_client as gc  # noqa: E402

PRIVATE_DETAIL = "private-token=secret-value private player conversation"


class UpstreamError(Exception):
    def __init__(self, code):
        super().__init__(PRIVATE_DETAIL)
        self.code = code


@pytest.mark.parametrize("code", [401, 404, 503, None])
def test_gemini_failures_do_not_expose_private_bodies(monkeypatch, caplog, code):
    def fail(_message):
        raise UpstreamError(code)

    sdk_client = SimpleNamespace(
        chats=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(send_message=fail)
        )
    )
    monkeypatch.setattr(
        gc,
        "_import_sdk",
        lambda: (SimpleNamespace(Client=lambda **kwargs: sdk_client), types, None),
    )
    client = gc.GeminiCoachClient(
        "test instruction", api_key="test-key", sleep=lambda _: None
    )
    with pytest.raises(gc.GeminiClientError) as error:
        client.send_message("test question")
    assert PRIVATE_DETAIL not in str(error.value)
    assert PRIVATE_DETAIL not in caplog.text
    assert error.value.__suppress_context__ is True
    assert caplog.records


def test_gemini_initialization_error_does_not_expose_private_body(monkeypatch, caplog):
    def fail(**kwargs):
        raise ValueError(PRIVATE_DETAIL)

    monkeypatch.setattr(
        gc, "_import_sdk", lambda: (SimpleNamespace(Client=fail), types, None)
    )
    with pytest.raises(gc.GeminiConfigurationError) as error:
        gc.GeminiCoachClient("test instruction", api_key="test-key")
    assert PRIVATE_DETAIL not in str(error.value)
    assert PRIVATE_DETAIL not in caplog.text
    assert error.value.__suppress_context__ is True
