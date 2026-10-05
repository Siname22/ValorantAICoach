import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import gemini_client as gc  # noqa: E402


def reply(request):
    return httpx.Response(
        200,
        request=request,
        json={
            "candidates": [{"content": {"role": "model", "parts": [{"text": "Reply"}]}}]
        },
    )


def test_real_sdk_requests_have_finite_transport_timeouts(monkeypatch):
    timeouts = []

    def send(self, request, **kwargs):
        timeouts.append(request.extensions["timeout"])
        return reply(request)

    monkeypatch.setattr(httpx.Client, "send", send)
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message("test question") == "Reply"
    finally:
        client.close()
    assert len(timeouts) == 1
    assert all(value is not None and 0 < value <= 10 for value in timeouts[0].values())


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError])
def test_real_transport_failures_retry_then_fallback(monkeypatch, error_type):
    paths = []
    sleeps = []

    def send(self, request, **kwargs):
        paths.append(request.url.path)
        if len(paths) <= 3:
            raise error_type("")
        return reply(request)

    monkeypatch.setattr(httpx.Client, "send", send)
    client = gc.GeminiCoachClient(
        "test instruction", api_key="test-key", sleep=sleeps.append
    )
    try:
        assert client.send_message("test question") == "Reply"
        assert client.active_model == "gemini-2.5-flash-lite"
    finally:
        client.close()
    assert len(paths) == 4
    assert all("gemini-2.5-flash:" in path for path in paths[:3])
    assert "gemini-2.5-flash-lite:" in paths[3]
    assert sleeps == [1.0, 2.0]
