"""Password hashing and JWT access tokens.

Passwords are hashed with Argon2id (argon2-cffi). Hashes produced by the
previous PBKDF2-HMAC-SHA256 implementation are still verified so existing
users can log in; ``password_needs_rehash`` tells the login flow to upgrade
them to Argon2id transparently.

Tokens are signed and validated with PyJWT. ``exp``, ``iat`` and ``sub`` are
mandatory: a token missing any of them is rejected.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

LEGACY_PBKDF2_PREFIX = "pbkdf2_sha256$"
REQUIRED_TOKEN_CLAIMS = ("exp", "iat", "sub")

_password_hasher = PasswordHasher()


def get_password_hash(password: str) -> str:
    """Hash a password with Argon2id."""
    return _password_hasher.hash(password)


def _verify_legacy_pbkdf2(plain_password: str, hashed_password: str) -> bool:
    try:
        _, iterations, salt_hex, key_hex = hashed_password.split("$")
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode(),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual, bytes.fromhex(key_hex))
    except (ValueError, TypeError):
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id or legacy PBKDF2 hash."""
    if hashed_password.startswith(LEGACY_PBKDF2_PREFIX):
        return _verify_legacy_pbkdf2(plain_password, hashed_password)
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """Return True for legacy hashes or Argon2 hashes with outdated parameters."""
    if hashed_password.startswith(LEGACY_PBKDF2_PREFIX):
        return True
    try:
        return _password_hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return True


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    """Create a signed JWT. ``data`` must contain ``sub``."""
    if "sub" not in data:
        raise ValueError("Access tokens require a 'sub' claim.")
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {**data, "sub": str(data["sub"]), "iat": now, "exp": expire}
    return jwt.encode(
        payload,
        secret_key or settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
    secret_key: str | None = None,
) -> dict[str, Any] | None:
    """Validate a JWT and return its claims, or None if it is not acceptable."""
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            secret_key or settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": list(REQUIRED_TOKEN_CLAIMS)},
        )
    except jwt.PyJWTError:
        return None
