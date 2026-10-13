import json
import shlex
import tomllib
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def devcontainer():
    with (REPOSITORY / ".devcontainer/devcontainer.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


def test_devcontainer_structure(devcontainer):
    assert devcontainer["name"] == "Valorant AI Coach Dev Container"
    assert "updateContentCommand" in devcontainer
    assert "uv sync" in devcontainer["updateContentCommand"]
    open_files = devcontainer["customizations"]["codespaces"]["openFiles"]
    assert "README.md" in open_files
    assert "backend/main.py" in open_files


def test_post_attach_backend_launch(devcontainer):
    command = shlex.split(devcontainer["postAttachCommand"]["backend"])
    assert command[0] == "uv"
    assert "uvicorn" in command
    assert "backend.main:app" in command
    assert "--port" in command
    port_index = command.index("--port")
    assert command[port_index + 1] == "8000"


def test_forwarded_ports_and_attributes(devcontainer):
    assert devcontainer["forwardPorts"] == [8000, 4200]
    assert devcontainer["portsAttributes"]["8000"] == {
        "label": "Backend API",
        "onAutoForward": "openPreview",
    }
    assert devcontainer["portsAttributes"]["4200"] == {
        "label": "Frontend Web (Angular)",
        "onAutoForward": "openPreview",
    }


def test_image_python_satisfies_project_requirement(devcontainer):
    with (REPOSITORY / "pyproject.toml").open("rb") as file:
        requirement = tomllib.load(file)["project"]["requires-python"]
    image, tag = devcontainer["image"].rsplit(":", 1)
    _, python_version, distribution = tag.split("-")

    assert python_version in SpecifierSet(requirement)
    assert image == "mcr.microsoft.com/devcontainers/python"
    assert distribution == "bookworm"
