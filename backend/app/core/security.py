import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.app.core.config import get_settings

PBKDF2_ITERATIONS = 100_000


def get_password_hash(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a cryptographically secure salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    salt_hex = salt.hex()
    key_hex = key.hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_hex}${key_hex}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored PBKDF2-HMAC-SHA256 hash in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        actual_key = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), salt, iterations
        )
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = len(data) % 4
    if padding > 0:
        data += "=" * (4 - padding)
    return base64.urlsafe_b64decode(data.encode())


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    """Create a standard signed HS256 JWT access token."""
    settings = get_settings()
    secret = (secret_key or settings.jwt_secret_key).encode()
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        **data,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

    encoded_header = _b64url_encode(header_bytes)
    encoded_payload = _b64url_encode(payload_bytes)
    signing_input = f"{encoded_header}.{encoded_payload}".encode()

    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(
    token: str,
    secret_key: str | None = None,
) -> dict[str, Any] | None:
    """Decode and verify an HS256 JWT access token. Returns claims dict or None."""
    settings = get_settings()
    secret = (secret_key or settings.jwt_secret_key).encode()

    parts = token.split(".")
    if len(parts) != 3:
        return None

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode()

    expected_signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    try:
        actual_signature = _b64url_decode(encoded_signature)
    except Exception:
        return None

    if not hmac.compare_digest(actual_signature, expected_signature):
        return None

    try:
        payload_bytes = _b64url_decode(encoded_payload)
        payload: dict[str, Any] = json.loads(payload_bytes.decode())
    except Exception:
        return None

    exp = payload.get("exp")
    if exp is not None and isinstance(exp, (int, float)) and exp < time.time():
        return None

    return payload
