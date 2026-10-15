import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Thread-safe in-memory token bucket rate limiter per client key."""

    def __init__(self, rate_per_minute: int = 120, burst: int = 30) -> None:
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = float(burst or rate_per_minute)
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_time)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> tuple[bool, int]:
        """Try to acquire 1 token. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        async with self._lock:
            # Periodic cleanup if cache gets very large (>10,000 keys)
            if len(self._buckets) > 10000:
                expired = [
                    k for k, (tokens, last) in self._buckets.items() if now - last > 300
                ]
                for k in expired:
                    del self._buckets[k]

            tokens, last_time = self._buckets.get(key, (self.capacity, now))
            # Replenish tokens based on elapsed time
            elapsed = now - last_time
            tokens = min(self.capacity, tokens + (elapsed * self.rate_per_second))

            if tokens >= 1.0:
                self._buckets[key] = (tokens - 1.0, now)
                return True, 0

            # Calculate wait time needed for 1 full token
            needed = 1.0 - tokens
            retry_after = max(1, int(needed / self.rate_per_second))
            self._buckets[key] = (tokens, now)
            return False, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce request rate limiting per IP to protect backend resources."""

    EXEMPT_PATHS = frozenset(
        {
            "/",
            "/health",
            "/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }
    )

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        *,
        enabled: bool = True,
        requests_per_minute: int = 120,
        burst: int = 30,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limiter = TokenBucketRateLimiter(
            rate_per_minute=requests_per_minute, burst=burst
        )

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        from backend.app.core.config import get_settings

        settings = get_settings()
        if not settings.rate_limit_enabled or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_key = self._get_client_key(request)
        if client_key == "testclient" and not getattr(
            settings, "rate_limit_testclient", False
        ):
            return await call_next(request)

        allowed, retry_after = await self.limiter.acquire(client_key)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for client %s on %s (retry_after=%ds)",
                client_key,
                request.url.path,
                retry_after,
            )
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
