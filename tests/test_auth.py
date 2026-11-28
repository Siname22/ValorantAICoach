from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import get_settings
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from backend.app.storage.models import UserRecord
from backend.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def auth_database(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    url = f"sqlite+pysqlite:///{(tmp_path / 'auth_coach.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database/migrations"))
    engine = create_engine(url)
    command.upgrade(config, "head")
    try:
        yield config, engine, url
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_password_hashing_and_verification():
    from backend.app.core.security import password_needs_rehash

    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password(password, "invalid$format$hash") is False
    assert verify_password(password, "corrupted") is False
    assert password_needs_rehash(hashed) is False

    # Legacy PBKDF2 compatibility
    legacy_hash = (
        "pbkdf2_sha256$100000$0123456789abcdef0123456789abcdef$"
        "c8109bf35a4d34a5d3fec45b40d6c4aa029f60a927a44f77c8e9d997cc93e110"
    )
    # Even if bad password, doesn't crash:
    assert verify_password("WrongPassword!", legacy_hash) is False
    assert password_needs_rehash(legacy_hash) is True


def test_jwt_token_creation_and_validation():
    import jwt

    data = {"sub": "user-uuid-1234", "email": "test@example.com"}
    token = create_access_token(data, expires_delta=timedelta(minutes=15))
    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == "user-uuid-1234"
    assert claims["email"] == "test@example.com"
    assert "exp" in claims
    assert "iat" in claims

    # Expired token
    expired_token = create_access_token(data, expires_delta=timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None

    # Token missing exp claim must be rejected
    settings = get_settings()
    token_without_exp = jwt.encode(
        {"sub": "user-uuid-1234", "iat": 1234567890},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert decode_access_token(token_without_exp) is None

    # Tampered signature
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.badsignature"
    assert decode_access_token(tampered_token) is None

    # Malformed token
    assert decode_access_token("not-a-jwt") is None


def test_user_registration_and_login_flow(auth_database):
    with TestClient(app) as client:
        # 1. Register new user
        reg_response = client.post(
            "/auth/register",
            json={"email": "player@example.com", "password": "SecurePassword123!"},
        )
        assert reg_response.status_code == 201
        user_data = reg_response.json()
        assert user_data["email"] == "player@example.com"
        assert user_data["is_active"] is True
        assert "id" in user_data

        # 2. Duplicate registration fails with 409
        dup_response = client.post(
            "/auth/register",
            json={"email": "player@example.com", "password": "SecurePassword123!"},
        )
        assert dup_response.status_code == 409

        # 3. Registration with password too short fails with 422
        short_pw = client.post(
            "/auth/register",
            json={"email": "short@example.com", "password": "short"},
        )
        assert short_pw.status_code == 422

        # 4. Login with correct password
        login_response = client.post(
            "/auth/login",
            json={"email": "player@example.com", "password": "SecurePassword123!"},
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        # 5. Login with incorrect password
        bad_pw_response = client.post(
            "/auth/login",
            json={"email": "player@example.com", "password": "WrongPassword!"},
        )
        assert bad_pw_response.status_code == 401

        # 6. Login with nonexistent user
        no_user_response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "SecurePassword123!"},
        )
        assert no_user_response.status_code == 401

        # 7. Get current user profile with token
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "player@example.com"
        assert me_data["id"] == user_data["id"]

        # 8. Get me without token
        unauth_response = client.get("/auth/me")
        assert unauth_response.status_code == 401


def test_inactive_user_access_is_forbidden(auth_database):
    _, engine, _ = auth_database
    with TestClient(app) as client:
        # Register user
        reg_response = client.post(
            "/auth/register",
            json={"email": "inactive@example.com", "password": "SecurePassword123!"},
        )
        assert reg_response.status_code == 201
        user_id = reg_response.json()["id"]

        # Mark user as inactive in database
        with Session(engine) as session, session.begin():
            user = session.get(UserRecord, user_id)
            user.is_active = False

        # Attempt to login fails with 403
        login_response = client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "SecurePassword123!"},
        )
        assert login_response.status_code == 403

        # Token created manually for inactive user fails with 403
        token = create_access_token({"sub": user_id, "email": "inactive@example.com"})
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 403


def test_linked_player_accounts_crud_and_primary_flag(auth_database):
    with TestClient(app) as client:
        # Register and login
        reg_res = client.post(
            "/auth/register",
            json={"email": "coach@example.com", "password": "SecurePassword123!"},
        )
        assert reg_res.status_code == 201
        token_response = client.post(
            "/auth/login",
            json={"email": "coach@example.com", "password": "SecurePassword123!"},
        )
        token = token_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Initially no accounts linked
        list_response = client.get("/auth/me/accounts", headers=auth_headers)
        assert list_response.status_code == 200
        assert list_response.json() == []

        # Link first account as primary
        acc1_response = client.post(
            "/auth/me/accounts",
            headers=auth_headers,
            json={
                "game_name": "Derke",
                "tag_line": "FNC",
                "region": "eu",
                "is_primary": True,
            },
        )
        assert acc1_response.status_code == 201
        acc1 = acc1_response.json()
        assert acc1["game_name"] == "Derke"
        assert acc1["tag_line"] == "FNC"
        assert acc1["is_primary"] is True

        # Link second account as primary -> first resets to is_primary=False
        acc2_response = client.post(
            "/auth/me/accounts",
            headers=auth_headers,
            json={
                "game_name": "TenZ",
                "tag_line": "SEN",
                "region": "na",
                "is_primary": True,
            },
        )
        assert acc2_response.status_code == 201
        acc2 = acc2_response.json()
        assert acc2["is_primary"] is True
        assert acc2["is_primary"] is True

        # Verify list shows both accounts and acc1 is no longer primary
        list_response2 = client.get("/auth/me/accounts", headers=auth_headers)
        assert list_response2.status_code == 200
        accounts = {a["game_name"]: a for a in list_response2.json()}
        assert len(accounts) == 2
        assert accounts["Derke"]["is_primary"] is False
        assert accounts["TenZ"]["is_primary"] is True

        # Delete acc1
        del_response = client.delete(
            f"/auth/me/accounts/{acc1['id']}", headers=auth_headers
        )
        assert del_response.status_code == 200
        assert del_response.json()["status"] == "deleted"

        # Verify only acc2 remains
        list_response3 = client.get("/auth/me/accounts", headers=auth_headers)
        assert len(list_response3.json()) == 1
        assert list_response3.json()[0]["game_name"] == "TenZ"

        # Deleting acc1 again returns 404
        del404 = client.delete(f"/auth/me/accounts/{acc1['id']}", headers=auth_headers)
        assert del404.status_code == 404


def test_account_isolation_between_users(auth_database):
    with TestClient(app) as client:
        # Register User A
        client.post(
            "/auth/register",
            json={"email": "usera@example.com", "password": "Password123!"},
        )
        token_a = client.post(
            "/auth/login",
            json={"email": "usera@example.com", "password": "Password123!"},
        ).json()["access_token"]

        # Register User B
        client.post(
            "/auth/register",
            json={"email": "userb@example.com", "password": "Password123!"},
        )
        token_b = client.post(
            "/auth/login",
            json={"email": "userb@example.com", "password": "Password123!"},
        ).json()["access_token"]

        # User A links an account
        acc_a = client.post(
            "/auth/me/accounts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"game_name": "Aspas", "tag_line": "LEV", "is_primary": True},
        ).json()

        # User B lists accounts -> should be empty
        list_b = client.get(
            "/auth/me/accounts",
            headers={"Authorization": f"Bearer {token_b}"},
        ).json()
        assert list_b == []

        # User B cannot delete User A's account -> 404
        del_attempt = client.delete(
            f"/auth/me/accounts/{acc_a['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert del_attempt.status_code == 404


def test_auth_endpoints_when_database_disabled(monkeypatch):
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    get_settings.cache_clear()
    with TestClient(app) as client:
        reg_response = client.post(
            "/auth/register",
            json={"email": "nodb@example.com", "password": "Password123!"},
        )
        assert reg_response.status_code == 503

        login_response = client.post(
            "/auth/login",
            json={"email": "nodb@example.com", "password": "Password123!"},
        )
        assert login_response.status_code == 503
    get_settings.cache_clear()


def test_admin_authorization_and_protected_costly_endpoints(auth_database, monkeypatch):
    config, engine, url = auth_database
    monkeypatch.setenv("ADMIN_EMAILS", "superadmin@example.com")
    get_settings.cache_clear()

    with TestClient(app) as client:
        # 1. Unauthenticated calls to costly or destructive endpoints return 401
        assert client.post("/players/Test/EU1/reports").status_code == 401
        assert client.post("/players/Test/EU1/sync").status_code == 401
        assert client.delete("/players/Test/EU1/cache").status_code == 401
        assert client.post("/vision/scoreboard/analyze", json={}).status_code == 401
        assert client.post("/system/cache/prune").status_code == 401
        assert client.post("/system/coaching/sync-tracked").status_code == 401

        # 2. Register regular user
        reg_reg = client.post(
            "/auth/register",
            json={"email": "regular@example.com", "password": "Password123!"},
        )
        assert reg_reg.status_code == 201
        assert reg_reg.json()["is_admin"] is False
        token_reg = client.post(
            "/auth/login",
            json={"email": "regular@example.com", "password": "Password123!"},
        ).json()["access_token"]
        headers_reg = {"Authorization": f"Bearer {token_reg}"}

        # Regular user gets 403 on /system/* endpoints
        res_prune = client.post("/system/cache/prune", headers=headers_reg)
        assert res_prune.status_code == 403
        res_sync = client.post("/system/coaching/sync-tracked", headers=headers_reg)
        assert res_sync.status_code == 403

        # 3. Attempting to register admin email via public registration
        # is forbidden (403)
        reg_admin_forbidden = client.post(
            "/auth/register",
            json={"email": "superadmin@example.com", "password": "AdminPassword123!"},
        )
        assert reg_admin_forbidden.status_code == 403
        assert "reserved" in reg_admin_forbidden.json()["detail"].lower()

        # 4. Provision admin user directly (as intended for administrative accounts)
        import uuid
        from datetime import UTC, datetime

        with Session(engine) as session, session.begin():
            u = UserRecord(
                id=str(uuid.uuid4()),
                email="superadmin@example.com",
                hashed_password=get_password_hash("AdminPassword123!"),
                is_active=True,
                is_admin=True,
                created_at=datetime.now(UTC),
            )
            session.add(u)

        token_admin = client.post(
            "/auth/login",
            json={"email": "superadmin@example.com", "password": "AdminPassword123!"},
        ).json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # Verify /auth/me returns is_admin=True for provisioned admin
        me_admin = client.get("/auth/me", headers=headers_admin)
        assert me_admin.status_code == 200
        assert me_admin.json()["is_admin"] is True

        # Admin user gets 200 on /system/* endpoints
        prune_res = client.post("/system/cache/prune", headers=headers_admin)
        assert prune_res.status_code == 200
        assert prune_res.json() == {"pruned_count": 0}

    get_settings.cache_clear()


def test_transparent_password_rehash_on_login(auth_database):
    config, engine, _ = auth_database
    legacy_hash = (
        "pbkdf2_sha256$100000$0123456789abcdef0123456789abcdef$"
        "c8109bf35a4d34a5d3fec45b40d6c4aa029f60a927a44f77c8e9d997cc93e110"
    )
    # Manually insert user with legacy PBKDF2 hash into database
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import select

    user_id = str(uuid.uuid4())
    with Session(engine) as session, session.begin():
        u = UserRecord(
            id=user_id,
            email="legacy@example.com",
            hashed_password=legacy_hash,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(UTC),
        )
        session.add(u)

    with TestClient(app) as client:
        # Before login, verify stored hash is legacy format
        with Session(engine) as session:
            stored_user = session.execute(
                select(UserRecord).where(UserRecord.email == "legacy@example.com")
            ).scalar_one()
            assert stored_user.hashed_password.startswith("pbkdf2_sha256$")

        # Login with correct password triggers transparent upgrade
        # Note: the salt/key above matches password "CorrectLegacyPassword123!"
        import hashlib

        salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
        expected_key = hashlib.pbkdf2_hmac(
            "sha256", b"MySecret123!", salt, 100_000
        ).hex()
        with Session(engine) as session, session.begin():
            u = session.get(UserRecord, user_id)
            u.hashed_password = (
                f"pbkdf2_sha256$100000$0123456789abcdef0123456789abcdef${expected_key}"
            )

        login_res = client.post(
            "/auth/login",
            json={"email": "legacy@example.com", "password": "MySecret123!"},
        )
        assert login_res.status_code == 200

        # After login, stored hash has been upgraded to Argon2id
        with Session(engine) as session:
            upgraded_user = session.execute(
                select(UserRecord).where(UserRecord.email == "legacy@example.com")
            ).scalar_one()
            assert upgraded_user.hashed_password.startswith("$argon2id$")
