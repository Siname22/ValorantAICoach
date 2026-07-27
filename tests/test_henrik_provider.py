import httpx
import pytest
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.henrik.config import HenrikConfig
from backend.providers.henrik.exceptions import (
    HenrikAuthenticationError,
    HenrikNotFoundError,
    HenrikRateLimitError,
)
from backend.providers.henrik.provider import HenrikProvider


@pytest.fixture
def henrik_config():
    return HenrikConfig(
        api_key="test-henrik-key", base_url="https://api.henrikdev.xyz/valorant/v1"
    )


@pytest.fixture
def henrik_provider(henrik_config):
    return HenrikProvider(henrik_config)


@pytest.mark.asyncio
@respx.mock
async def test_henrik_health_check_success(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/status/eu").mock(
        return_value=httpx.Response(200)
    )
    health = await henrik_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_get_account_success(henrik_provider):
    mock_data = {
        "status": 200,
        "data": {
            "puuid": "test-puuid",
            "name": "Player",
            "tag": "123",
            "region": "eu",
            "account_level": 50,
        },
    }
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    player = await henrik_provider.get_account("Player", "123")
    assert player.name == "Player"
    assert player.puuid == "test-puuid"
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_get_matches_success(henrik_provider):
    mock_data = {
        "status": 200,
        "data": [
            {
                "metadata": {
                    "map": "Ascent",
                    "game_version": "release-01.00",
                    "game_length": 1800,
                    "game_start": 1600000000,
                    "mode": "Competitive",
                },
                "players": [],
                "teams": {},
                "rounds": [],
            }
        ],
    }
    respx.get(
        "https://api.henrikdev.xyz/valorant/v1/lifetime/matches/eu/Player/123"
    ).mock(return_value=httpx.Response(200, json=mock_data))

    matches = await henrik_provider.get_matches("eu", "Player", "123")
    assert len(matches) == 1
    assert matches[0].metadata.map == "Ascent"
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_not_found(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/NonExistent/000").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(HenrikNotFoundError):
        await henrik_provider.get_account("NonExistent", "000")
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_auth_failed(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(HenrikAuthenticationError):
        await henrik_provider.get_account("Player", "123")
    await henrik_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_henrik_error_mapping_rate_limit(henrik_provider):
    respx.get("https://api.henrikdev.xyz/valorant/v1/account/Player/123").mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(HenrikRateLimitError):
        await henrik_provider.get_account("Player", "123")
    await henrik_provider.close()
