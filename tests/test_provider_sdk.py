import httpx
import pytest
import respx
from agents.shared.container import container
from backend.providers.base.client import BaseHTTPClient
from backend.providers.base.config import ProviderConfig
from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

# --- Mock Provider Implementation ---


class MockProviderConfig(ProviderConfig):
    base_url: str = "https://api.mockprovider.com"
    api_key: str = "test-api-key"


class MockProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "mock_provider"

    async def health_check(self) -> ProviderHealth:
        try:
            response = await self.client.get("/health")
            if response.status_code == 200:
                return ProviderHealth(status=ProviderStatus.HEALTHY, message="OK")
        except Exception as e:
            return ProviderHealth(status=ProviderStatus.UNHEALTHY, message=str(e))
        return ProviderHealth(
            status=ProviderStatus.UNHEALTHY, message="Unexpected response"
        )


# --- Tests ---


@pytest.mark.asyncio
@respx.mock
async def test_http_client_get_success():
    config = MockProviderConfig()
    client = BaseHTTPClient(config, "test_provider")

    respx.get("https://api.mockprovider.com/test").mock(
        return_value=httpx.Response(200, json={"foo": "bar"})
    )

    response = await client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"foo": "bar"}
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_http_client_auth_api_key():
    config = MockProviderConfig()
    client = BaseHTTPClient(config, "test_provider")

    mock_route = respx.get("https://api.mockprovider.com/auth-test").mock(
        return_value=httpx.Response(200)
    )

    await client.get("/auth-test", auth_type="api_key")
    assert mock_route.calls.last.request.headers["X-API-Key"] == "test-api-key"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_http_client_retries_on_500():
    config = MockProviderConfig(retries=2, backoff_factor=0.01)
    client = BaseHTTPClient(config, "test_provider")

    mock_route = respx.get("https://api.mockprovider.com/retry-test").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"success": True}),
        ]
    )

    response = await client.get("/retry-test")
    assert response.status_code == 200
    assert mock_route.call_count == 3
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_http_client_timeout_error():
    config = MockProviderConfig(retries=0, timeout=0.01)
    client = BaseHTTPClient(config, "test_provider")

    respx.get("https://api.mockprovider.com/timeout").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    with pytest.raises(TimeoutError):
        await client.get("/timeout")
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_http_client_error_mapping():
    config = MockProviderConfig(retries=0)
    client = BaseHTTPClient(config, "test_provider")

    respx.get("https://api.mockprovider.com/401").mock(return_value=httpx.Response(401))
    respx.get("https://api.mockprovider.com/404").mock(return_value=httpx.Response(404))
    respx.get("https://api.mockprovider.com/429").mock(return_value=httpx.Response(429))
    respx.get("https://api.mockprovider.com/500").mock(return_value=httpx.Response(500))

    with pytest.raises(AuthenticationError):
        await client.get("/401")
    with pytest.raises(NotFoundError):
        await client.get("/404")
    with pytest.raises(RateLimitError):
        await client.get("/429")
    with pytest.raises(ServerError):
        await client.get("/500")
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_provider_health_check():
    config = MockProviderConfig()
    provider = MockProvider(config)

    respx.get("https://api.mockprovider.com/health").mock(
        return_value=httpx.Response(200)
    )

    health = await provider.health_check()
    assert health.status == ProviderStatus.HEALTHY
    await provider.close()


def test_dependency_injection_resolve_by_type():
    container.reset()
    config = MockProviderConfig()
    provider = MockProvider(config)

    container.register_provider("mock", provider)

    resolved_provider = container.resolve(MockProvider)
    assert resolved_provider == provider
    assert resolved_provider.name == "mock_provider"

    # Test resolving by base class
    resolved_base = container.resolve(BaseProvider)
    assert resolved_base == provider
