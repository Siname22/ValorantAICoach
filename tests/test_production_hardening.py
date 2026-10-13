from __future__ import annotations

from backend.main import app
from fastapi.testclient import TestClient


def test_security_headers_present_on_endpoints():
    with TestClient(app) as client:
        res = client.get("/health/live")
        assert res.status_code == 200
        headers = res.headers

        # Check defensive security headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert (
            headers.get("permissions-policy")
            == "geolocation=(), camera=(), microphone=()"
        )
        assert (
            headers.get("content-security-policy")
            == "default-src 'self'; frame-ancestors 'none';"
        )


def test_cors_preflight_and_allowed_origin():
    with TestClient(app) as client:
        # Preflight OPTIONS request from allowed origin
        res = client.options(
            "/health/live",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:8501"
        assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallows_unauthorized_origin():
    with TestClient(app) as client:
        res = client.get(
            "/health/live",
            headers={"Origin": "https://malicious-site.example.com"},
        )
        assert res.status_code == 200
        # Disallowed origin should NOT be echoed in access-control-allow-origin
        assert (
            res.headers.get("access-control-allow-origin")
            != "https://malicious-site.example.com"
        )


def test_oversized_payload_rejected_with_413(monkeypatch):

    # Verify that a request header claiming to exceed the max size is rejected
    with TestClient(app) as client:
        # Construct header with oversized Content-Length
        res = client.post(
            "/vision/scoreboard/analyze",
            headers={"Content-Length": str(100 * 1024 * 1024)},  # 100 MB
            json={"image_base64": "dummy"},
        )
        assert res.status_code == 413
        assert "Payload Too Large" in res.json().get("detail", "")
