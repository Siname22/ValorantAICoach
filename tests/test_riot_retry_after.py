import os
from unittest.mock import AsyncMock, call

import httpx
import pytest
import pytest_asyncio
import respx
from backend.providers.riot.client import RiotHTTPClient
from backend.providers.riot.config import RiotConfig
from backend.providers.riot.exceptions import RiotRateLimitError

STATUS_URL = "https://eu.api.riotgames.com/val/status/v1/platform-data"
STATUS_ENDPOINT = "/val/status/v1/platform-data"


@pytest.fixture(autouse=True)
def isolate_riot_environment(monkeypatch):
    for name in os.environ:
        if name.startswith("RIOT_"):
            monkeypatch.delenv(name)


@pytest_asyncio.fixture
async def riot_client():
    config = RiotConfig(
        api_key="test-riot-key",
        base_url="https://eu.api.riotgames.com",
        timeout=0.01,
        retries=1,
        backoff_factor=0.5,
        default_headers={},
        _env_file=None,
    )
    client = RiotHTTPClient(config, provider_name="riot")
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def sleep(monkeypatch):
    intercepted_sleep = AsyncMock()
    monkeypatch.setattr(
        "backend.providers.base.client.asyncio.sleep", intercepted_sleep
    )
    return intercepted_sleep


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("retry_after", "expected_wait"),
    [
        pytest.param("1e9", 30.0, id="billion-seconds"),
        pytest.param("1e308", 30.0, id="huge-finite"),
        pytest.param("30.001", 30.0, id="above-cap"),
        pytest.param("30", 30.0, id="at-cap"),
        pytest.param("29.999", 29.999, id="below-cap"),
        pytest.param("2", 2.0, id="short-delay"),
        pytest.param("0", 0.0, id="zero"),
        pytest.param(None, 0.5, id="absent"),
        pytest.param("", 0.5, id="empty"),
        pytest.param("invalid", 0.5, id="malformed"),
        pytest.param("-1", 0.5, id="negative"),
        pytest.param("inf", 0.5, id="infinity"),
        pytest.param("-inf", 0.5, id="negative-infinity"),
        pytest.param("nan", 0.5, id="nan"),
        pytest.param("1e309", 0.5, id="overflow-to-infinity"),
    ],
)
async def test_riot_retry_after_bounds_wait_and_preserves_fallback(
    riot_client, sleep, retry_after, expected_wait
):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    route = respx.get(STATUS_URL).mock(
        side_effect=[
            httpx.Response(429, headers=headers),
            httpx.Response(200, json={"status": "ok"}),
        ]
    )

    response = await riot_client.get(STATUS_ENDPOINT)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert route.call_count == 2
    sleep.assert_awaited_once_with(expected_wait)


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("retries", "expected_requests", "expected_waits"),
    [(0, 1, []), (1, 2, [30.0]), (2, 3, [30.0, 30.0])],
)
async def test_riot_retry_after_cap_preserves_retry_budget_and_final_error(
    riot_client, sleep, retries, expected_requests, expected_waits
):
    riot_client.config.retries = retries
    route = respx.get(STATUS_URL).respond(
        429, headers={"Retry-After": "1e9"}, text="rate limited"
    )

    with pytest.raises(RiotRateLimitError) as error:
        await riot_client.get(STATUS_ENDPOINT)

    assert error.value.status_code == 429
    assert error.value.response_body == "rate limited"
    assert error.value.retry_after == 30.0
    assert route.call_count == expected_requests
    assert sleep.await_args_list == [call(wait) for wait in expected_waits]


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("retry_after", [None, "invalid", "-1", "inf", "nan"])
async def test_riot_retry_after_fallback_preserves_exponential_backoff(
    riot_client, sleep, retry_after
):
    riot_client.config.retries = 2
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    route = respx.get(STATUS_URL).mock(
        side_effect=[
            httpx.Response(429, headers=headers),
            httpx.Response(429, headers=headers),
            httpx.Response(200, json={"status": "ok"}),
        ]
    )

    response = await riot_client.get(STATUS_ENDPOINT)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert route.call_count == 3
    assert sleep.await_args_list == [call(0.5), call(1.0)]
