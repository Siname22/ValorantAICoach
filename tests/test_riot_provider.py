import httpx
import pytest
import respx
from backend.providers.base.models import ProviderStatus
from backend.providers.riot.config import RiotConfig
from backend.providers.riot.exceptions import (
    RiotAuthenticationError,
    RiotNotFoundError,
    RiotRateLimitError,
)
from backend.providers.riot.provider import RiotProvider


@pytest.fixture
def riot_config():
    return RiotConfig(
        api_key="test-riot-key",
        base_url="https://americas.api.riotgames.com/valorant/v1",
        region="na",
    )


@pytest.fixture
def riot_provider(riot_config):
    return RiotProvider(riot_config)


@pytest.mark.asyncio
@respx.mock
async def test_riot_health_check_success(riot_provider):
    respx.get("https://americas.api.riotgames.com/valorant/v1/").mock(
        return_value=httpx.Response(200)
    )
    health = await riot_provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    await riot_provider.close()


@pytest.mark.asyncio
async def test_riot_get_player_by_riot_id_mocked(riot_provider):
    # This test relies on the mocked implementation within RiotProvider
    player = await riot_provider.get_player_by_riot_id("Player", "123")
    assert player.game_name == "Player"
    assert player.tag_line == "123"
    assert player.puuid == "mock-puuid-123"
    assert player.region == "na"
    await riot_provider.close()


@pytest.mark.asyncio
async def test_riot_get_player_match_history_mocked(riot_provider):
    # This test relies on the mocked implementation within RiotProvider
    matches = await riot_provider.get_player_match_history("mock-puuid-123")
    assert len(matches) == 2
    assert matches[0].match_id == "mock-match-1"
    assert matches[1].player_stats.agent_name == "Raze"
    await riot_provider.close()


@pytest.mark.asyncio
async def test_riot_get_player_rank_mocked(riot_provider):
    # This test relies on the mocked implementation within RiotProvider
    rank = await riot_provider.get_player_rank("mock-puuid-123")
    assert rank.tier == "Immortal"
    assert rank.rank == "Immortal 3"
    assert rank.ranked_rating == 800
    await riot_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_riot_error_mapping_not_found(riot_provider):
    respx.get("https://americas.api.riotgames.com/valorant/v1/nonexistent").mock(
        return_value=httpx.Response(404)
    )

    # For mocked methods, we need to call a real HTTP endpoint
    # to trigger the error mapping
    # Since get_player_by_riot_id is mocked, we'll use a dummy client call
    with pytest.raises(RiotNotFoundError):
        await riot_provider.client.get("/nonexistent", auth_type="api_key")
    await riot_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_riot_error_mapping_auth_failed(riot_provider):
    respx.get("https://americas.api.riotgames.com/valorant/v1/auth").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(RiotAuthenticationError):
        await riot_provider.client.get("/auth", auth_type="api_key")
    await riot_provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_riot_error_mapping_rate_limit(riot_provider):
    respx.get("https://americas.api.riotgames.com/valorant/v1/ratelimit").mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(RiotRateLimitError):
        await riot_provider.client.get("/ratelimit", auth_type="api_key")
    await riot_provider.close()
