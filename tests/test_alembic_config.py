from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import get_settings
from sqlalchemy.engine import Engine

URL_CASES = [
    pytest.param("example", "example", "example", "example", id="plain"),
    pytest.param(
        "example%40user",
        "example%25secret%40test",
        "example@user",
        "example%secret@test",
        id="encoded-credentials",
    ),
    pytest.param(
        "example", "%3A%2F%3F%23%5B%5D%40", "example", ":/?#[]@", id="separators"
    ),
    pytest.param("example", "%25%25", "example", "%%", id="repeated-percent"),
]


@pytest.fixture
def migration_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(output_buffer=StringIO())
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "database/migrations")
    )
    try:
        yield config
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("user,password,decoded_user,decoded_password", URL_CASES)
def test_offline_migration_preserves_encoded_database_url(
    migration_config, monkeypatch, user, password, decoded_user, decoded_password
):
    url = f"postgresql+psycopg://{user}:{password}@127.0.0.1:1/example"
    monkeypatch.setenv("DATABASE_URL", url)

    def forbid_connect(self):
        pytest.fail("Offline SQL generation must not connect to a database")

    monkeypatch.setattr(Engine, "connect", forbid_connect)
    try:
        command.upgrade(migration_config, "head", sql=True)
    except ValueError as error:
        pytest.fail(f"Alembic rejected a valid configured URL: {type(error).__name__}")

    assert migration_config.get_main_option("sqlalchemy.url") == url
    assert "BEGIN;" in migration_config.output_buffer.getvalue()
    assert "COMMIT;" in migration_config.output_buffer.getvalue()


@pytest.mark.parametrize("user,password,decoded_user,decoded_password", URL_CASES)
def test_online_migration_passes_original_credentials_to_engine(
    migration_config, monkeypatch, user, password, decoded_user, decoded_password
):
    url = f"postgresql+psycopg://{user}:{password}@127.0.0.1:1/example"
    monkeypatch.setenv("DATABASE_URL", url)
    engine_urls = []

    class ConnectionIntercepted(Exception):
        pass

    def intercept_connect(self):
        engine_urls.append(self.url)
        raise ConnectionIntercepted

    monkeypatch.setattr(Engine, "connect", intercept_connect)
    try:
        with pytest.raises(ConnectionIntercepted):
            command.upgrade(migration_config, "head")
    except ValueError as error:
        pytest.fail(f"Alembic rejected a valid configured URL: {type(error).__name__}")

    assert migration_config.get_main_option("sqlalchemy.url") == url
    assert len(engine_urls) == 1
    assert engine_urls[0].username == decoded_user
    assert engine_urls[0].password == decoded_password
    assert engine_urls[0].host == "127.0.0.1"
    assert engine_urls[0].port == 1
