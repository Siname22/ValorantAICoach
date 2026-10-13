from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth HTTP security headers on all responses."""

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        *,
        enable_hsts: bool = True,
        content_security_policy: str = "default-src 'self'; frame-ancestors 'none';",
    ) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.content_security_policy = content_security_policy

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Baseline security headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), camera=(), microphone=()"
        )

        if self.content_security_policy:
            response.headers.setdefault(
                "Content-Security-Policy", self.content_security_policy
            )

        if self.enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class ContentLengthLimitMiddleware(BaseHTTPMiddleware):
    """Guard against oversized HTTP request bodies to prevent memory exhaustion."""

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        max_content_length: int = 25 * 1024 * 1024,  # 25 MB default
    ) -> None:
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_content_length:
                    logger.warning(
                        "Rejected request with payload size %d bytes (limit: %d)",
                        length,
                        self.max_content_length,
                    )
                    return Response(
                        content='{"detail":"Payload Too Large"}',
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        media_type="application/json",
                    )
            except ValueError:
                pass

        return await call_next(request)
