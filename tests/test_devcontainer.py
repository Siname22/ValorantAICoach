import json
import os
import shlex
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from click.testing import CliRunner
from packaging.specifiers import SpecifierSet
from streamlit import config, net_util
from streamlit.runtime.secrets import secrets_singleton
from streamlit.web import bootstrap, cli
from streamlit.web.server import server_util

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def devcontainer():
    with (REPOSITORY / ".devcontainer/devcontainer.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


@pytest.fixture
def configured_launch(devcontainer, monkeypatch):
    command = shlex.split(devcontainer["postAttachCommand"]["server"])
    assert command[0] == "streamlit"
    monkeypatch.chdir(REPOSITORY)
    for name in os.environ:
        if name.startswith("STREAMLIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("STREAMLIT_SERVER_ENABLE_CORS", "false")
    monkeypatch.setenv("STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION", "false")

    # Keep CLI parsing/configuration real; isolate user files and startup effects.
    monkeypatch.setattr(config, "_config_options", None)
    monkeypatch.setattr(config, "_main_script_path", None, raising=False)
    monkeypatch.setattr(config, "get_config_files", lambda file_name: [])
    monkeypatch.setattr(secrets_singleton, "load_if_toml_exists", lambda: False)
    monkeypatch.setattr(cli, "check_credentials", lambda: None)
    monkeypatch.setattr(net_util, "get_internal_ip", lambda: "192.0.2.10")
    monkeypatch.setattr(net_util, "get_external_ip", lambda: "198.51.100.10")
    launches = []

    def intercept_run(main_script_path, is_hello, args, config_flags):
        launches.append(
            {
                "main_script_path": Path(main_script_path),
                "is_hello": is_hello,
                "args": args,
                "config_flags": config_flags.copy(),
                "effective": {
                    "server.enableCORS": config.get_option("server.enableCORS"),
                    "server.enableXsrfProtection": config.get_option(
                        "server.enableXsrfProtection"
                    ),
                    "server.port": config.get_option("server.port"),
                },
            }
        )

    monkeypatch.setattr(bootstrap, "run", intercept_run)
    result = CliRunner().invoke(cli.main, command[1:], prog_name="streamlit")
    assert result.exit_code == 0, result.output
    assert len(launches) == 1
    return launches[0]


# Catch disabled or omitted CLI flags even when Streamlit defaults enable them.
@pytest.mark.parametrize("option", ["server.enableCORS", "server.enableXsrfProtection"])
def test_post_attach_enables_protections(configured_launch, option):
    assert configured_launch["config_flags"][option.replace(".", "_")] is True
    assert configured_launch["effective"][option] is True


# Catch permissive CORS while retaining access through the forwarded local port.
@pytest.mark.parametrize(
    "origin,allowed",
    [
        pytest.param("http://localhost:8501", True, id="local-preview"),
        pytest.param("https://unrelated.example", False, id="unrelated-origin"),
    ],
)
def test_post_attach_origin_policy(configured_launch, origin, allowed):
    assert server_util.is_url_from_allowed_origins(origin) is allowed


def test_post_attach_preserves_app_and_forwarded_port(configured_launch, devcontainer):
    assert configured_launch["main_script_path"] == (
        REPOSITORY / "frontend/streamlit_app/app.py"
    )
    assert configured_launch["is_hello"] is False
    assert not configured_launch["args"]
    assert configured_launch["effective"]["server.port"] == 8501
    assert devcontainer["forwardPorts"] == [8501]
    assert devcontainer["portsAttributes"]["8501"] == {
        "label": "Application",
        "onAutoForward": "openPreview",
    }


# Catch an image whose declared Python version cannot run the project.
def test_image_python_satisfies_project_requirement(devcontainer):
    with (REPOSITORY / "pyproject.toml").open("rb") as file:
        requirement = tomllib.load(file)["project"]["requires-python"]
    image, tag = devcontainer["image"].rsplit(":", 1)
    _, python_version, distribution = tag.split("-")

    assert python_version in SpecifierSet(requirement)
    assert image == "mcr.microsoft.com/devcontainers/python"
    assert distribution == "bookworm"
