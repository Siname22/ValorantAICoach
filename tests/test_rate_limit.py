import asyncio

import pytest
from backend.app.middleware.rate_limit import (
    RateLimitMiddleware,
    TokenBucketRateLimiter,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_acquire_and_exhaust():
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst=3)
    key = "client-1"

    # First 3 requests (burst) are allowed
    for _ in range(3):
        allowed, retry_after = await limiter.acquire(key)
        assert allowed is True
        assert retry_after == 0

    # 4th request exceeds burst capacity
    allowed, retry_after = await limiter.acquire(key)
    assert allowed is False
    assert retry_after >= 1


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_replenishment():
    limiter = TokenBucketRateLimiter(rate_per_minute=600, burst=2)  # 10 tokens/sec
    key = "client-fast"

    # Consume all tokens
    assert (await limiter.acquire(key))[0] is True
    assert (await limiter.acquire(key))[0] is True
    assert (await limiter.acquire(key))[0] is False

    # Sleep 0.2s -> replenishes ~2 tokens
    await asyncio.sleep(0.2)
    allowed, _ = await limiter.acquire(key)
    assert allowed is True


def test_rate_limit_middleware_blocks_excess_and_exempts_health():
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=60,
        burst=2,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/test-endpoint")
    def test_endpoint():
        return {"result": "success"}

    client = TestClient(app)
    headers = {"X-Forwarded-For": "198.51.100.1"}

    # 1. Normal requests within burst capacity (burst=2)
    r1 = client.get("/api/test-endpoint", headers=headers)
    assert r1.status_code == 200

    r2 = client.get("/api/test-endpoint", headers=headers)
    assert r2.status_code == 200

    # 2. 3rd request triggers 429 Too Many Requests
    r3 = client.get("/api/test-endpoint", headers=headers)
    assert r3.status_code == 429
    assert "rate limit exceeded" in r3.json()["detail"].lower()
    assert "Retry-After" in r3.headers

    # 3. Exempt path (/health) remains accessible even when rate limit triggered
    r_health = client.get("/health", headers=headers)
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"
