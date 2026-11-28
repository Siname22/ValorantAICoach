import asyncio

import pytest
from backend.app.middleware.rate_limit import (
    RateLimitMiddleware,
    TokenBucketRateLimiter,
)
from backend.app.middleware.security import SecurityHeadersMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


def test_rate_limit_exempts_all_health_probes():
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=60,
        burst=1,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/health/live")
    def live():
        return {"status": "live"}

    @app.get("/health/ready")
    def ready():
        return {"status": "ready"}

    @app.get("/api/data")
    def data():
        return {"data": 123}

    client = TestClient(app)

    # Exhaust quota on normal endpoint (burst=1)
    assert client.get("/api/data").status_code == 200
    assert client.get("/api/data").status_code == 429

    # All health probes remain exempt and return 200 even after exhaustion
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_rate_limit_429_preserves_cors_and_security_headers():
    app = FastAPI()

    # 1. Innermost: Rate limiter
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=60,
        burst=1,
    )
    # 2. Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=False,
    )
    # 3. Outermost: CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/action")
    def action():
        return {"ok": True}

    client = TestClient(app)
    origin_header = {"Origin": "http://localhost:4200"}

    # Request 1: 200 OK with CORS & Security headers
    r1 = client.get("/api/action", headers=origin_header)
    assert r1.status_code == 200
    assert r1.headers.get("access-control-allow-origin") == "http://localhost:4200"
    assert r1.headers.get("x-content-type-options") == "nosniff"

    # Request 2: 429 Too Many Requests MUST also preserve CORS & Security headers
    r2 = client.get("/api/action", headers=origin_header)
    assert r2.status_code == 429
    assert r2.headers.get("access-control-allow-origin") == "http://localhost:4200"
    assert r2.headers.get("x-content-type-options") == "nosniff"
    assert r2.headers.get("x-frame-options") == "DENY"
    assert "Retry-After" in r2.headers


def test_rate_limit_cannot_be_bypassed_via_spoofed_x_forwarded_for():
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=60,
        burst=2,
    )

    @app.get("/api/action")
    def action():
        return {"ok": True}

    # Simulate an external client (peer IP 203.0.113.195, NOT a trusted reverse proxy)
    client = TestClient(app, client=("203.0.113.195", 50123))

    # Request 1: Claims to be 10.0.0.1
    r1 = client.get("/api/action", headers={"X-Forwarded-For": "10.0.0.1"})
    assert r1.status_code == 200

    # Request 2: Attempts to spoof new identity 10.0.0.2
    r2 = client.get("/api/action", headers={"X-Forwarded-For": "10.0.0.2"})
    assert r2.status_code == 200

    # Request 3: Attempts to spoof 10.0.0.3 -> BLOCKED!
    # Because peer IP 203.0.113.195 is untrusted, X-Forwarded-For is ignored,
    # and all requests are counted toward 203.0.113.195.
    r3 = client.get("/api/action", headers={"X-Forwarded-For": "10.0.0.3"})
    assert r3.status_code == 429


def _trusted_proxy_client(trusted_proxies):
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=1,
        burst=1,
        trusted_proxies=trusted_proxies,
    )

    @app.get("/api/action")
    def action():
        return {"ok": True}

    return TestClient(app, client=("10.0.0.10", 50123))


@pytest.mark.parametrize(
    ("first_header", "second_header", "trusted_proxies"),
    [
        (
            "198.51.100.1, 203.0.113.50",
            "198.51.100.2, 203.0.113.50",
            frozenset({"10.0.0.10"}),
        ),
        (
            "198.51.100.1, 203.0.113.50, 10.0.0.20",
            "198.51.100.2, 203.0.113.50, 10.0.0.20",
            frozenset({"10.0.0.10", "10.0.0.20"}),
        ),
        (
            "2001:0db8:0000:0000:0000:0000:0000:0050",
            "2001:db8::50",
            frozenset({"10.0.0.10"}),
        ),
        (
            "invalid-client-one",
            "invalid-client-two",
            frozenset({"10.0.0.10"}),
        ),
    ],
    ids=["appending-proxy", "proxy-chain", "ipv6-aliases", "invalid-addresses"],
)
def test_trusted_proxy_cannot_supply_fresh_quota_for_same_client(
    first_header, second_header, trusted_proxies
):
    with _trusted_proxy_client(trusted_proxies) as client:
        assert (
            client.get(
                "/api/action", headers={"X-Forwarded-For": first_header}
            ).status_code
            == 200
        )
        assert (
            client.get(
                "/api/action", headers={"X-Forwarded-For": second_header}
            ).status_code
            == 429
        )


@pytest.mark.parametrize(
    ("proxy_hop", "trusted_proxy"),
    [
        ("", "10.0.0.10"),
        ("10.0.0.20", "10.0.0.20"),
        (
            "2001:db8::20",
            "2001:0db8:0000:0000:0000:0000:0000:0020",
        ),
        (
            "2001:0db8:0000:0000:0000:0000:0000:0020",
            "2001:db8::20",
        ),
    ],
    ids=["one-proxy", "two-proxies", "expanded-trusted-ipv6", "expanded-hop-ipv6"],
)
def test_trusted_proxy_preserves_independent_client_quotas(proxy_hop, trusted_proxy):
    proxies = frozenset({"10.0.0.10", trusted_proxy})
    suffix = f", {proxy_hop}" if proxy_hop else ""
    with _trusted_proxy_client(proxies) as client:
        alice = {"X-Forwarded-For": f"203.0.113.50{suffix}"}
        bob = {"X-Forwarded-For": f"203.0.113.51{suffix}"}
        assert client.get("/api/action", headers=alice).status_code == 200
        assert client.get("/api/action", headers=alice).status_code == 429
        assert client.get("/api/action", headers=bob).status_code == 200
