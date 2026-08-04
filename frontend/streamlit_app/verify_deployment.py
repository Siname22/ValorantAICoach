"""Deployment readiness check for the Streamlit frontend.

Simulates how Streamlit Community Cloud loads the app (process launched from the
repository root) and validates that:

1. The dependency file Community Cloud will actually pick up is the frontend one
   and that it declares every third-party package the app imports.
2. The entrypoint and every page script can be imported without errors.

Community Cloud resolves dependencies from the FIRST file it finds, searching the
entrypoint directory before the repository root, with this priority:

    uv.lock > Pipfile > environment.yml > requirements.txt > pyproject.toml

Run from the repository root:

    python frontend/streamlit_app/verify_deployment.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]

SCRIPTS = [
    APP_DIR / "app.py",
    *sorted((APP_DIR / "pages").glob("*.py")),
]

# Dependency filenames in Community Cloud priority order.
DEPENDENCY_FILES = (
    "uv.lock",
    "Pipfile",
    "environment.yml",
    "requirements.txt",
    "pyproject.toml",
)

# Third-party packages imported by the frontend, mapped to their PyPI names.
REQUIRED_PACKAGES = {
    "streamlit": "streamlit",
    "requests": "requests",
    "plotly": "plotly",
    "pandas": "pandas",
}

BACKEND_ONLY = {"fastapi", "uvicorn", "sqlalchemy", "alembic", "psycopg"}


def _resolved_dependency_file() -> Path | None:
    """Return the dependency file Community Cloud would use, if any."""
    for directory in (APP_DIR, REPO_ROOT):
        for filename in DEPENDENCY_FILES:
            candidate = directory / filename
            if candidate.exists():
                return candidate
    return None


def _parse_requirement_names(path: Path) -> list[tuple[str, str]]:
    """Return ``(normalized_name, raw_line)`` pairs from a requirements file."""
    entries: list[tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = line.split("[")[0]
        for separator in (">", "<", "=", "!", "~", ";", " "):
            name = name.split(separator)[0]
        entries.append((name.strip().lower(), raw_line))
    return entries


def _check_dependencies() -> list[str]:
    """Validate the dependency file Community Cloud will actually install."""
    problems: list[str] = []

    resolved = _resolved_dependency_file()
    if resolved is None:
        return ["No dependency file found in the entrypoint directory or root"]

    print(f"Community Cloud will install: {resolved.relative_to(REPO_ROOT)}")

    expected = APP_DIR / "requirements.txt"
    if resolved != expected:
        problems.append(
            f"Community Cloud would resolve {resolved.relative_to(REPO_ROOT)} "
            f"instead of {expected.relative_to(REPO_ROOT)}; the frontend "
            "requirements file must sit next to app.py to take precedence"
        )
        return problems

    declared = _parse_requirement_names(resolved)
    declared_names = {name for name, _ in declared}

    for raw_name, pypi_name in REQUIRED_PACKAGES.items():
        if pypi_name.lower() not in declared_names:
            problems.append(
                f"{resolved.name} is missing required package: {raw_name}"
            )

    for name, raw_line in declared:
        if not name.replace("-", "").replace("_", "").replace(".", "").isalnum():
            problems.append(f"{resolved.name} has an invalid entry: {raw_line!r}")
        elif name in BACKEND_ONLY:
            problems.append(f"{resolved.name} contains a backend package: {name}")

    return problems


def _check_imports() -> list[str]:
    """Confirm that every required third-party package is importable."""
    problems: list[str] = []
    for module_name in REQUIRED_PACKAGES:
        try:
            __import__(module_name)
        except ImportError as exc:
            problems.append(f"cannot import {module_name}: {exc}")
        else:
            print(f"OK  import {module_name}")
    try:
        import plotly.graph_objects  # noqa: F401
    except ImportError as exc:
        problems.append(f"cannot import plotly.graph_objects: {exc}")
    else:
        print("OK  import plotly.graph_objects")
    return problems


def _check_scripts() -> list[str]:
    """Import every Streamlit script in isolation and report failures."""
    problems: list[str] = []
    for script in SCRIPTS:
        module_name = f"__verify_{script.stem}__"
        try:
            runpy.run_path(str(script), run_name=module_name)
        except Exception as exc:  # noqa: BLE001 - report every failure
            problems.append(f"{script.relative_to(REPO_ROOT)} failed: {exc!r}")
        else:
            print(f"OK  {script.relative_to(REPO_ROOT)}")
    return problems


def main() -> int:
    print(f"Repository root: {REPO_ROOT}")
    print(f"Python: {sys.version.split()[0]}\n")

    problems = _check_dependencies() + _check_imports() + _check_scripts()

    print()
    if problems:
        print("Deployment check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("Deployment check PASSED: dependencies resolve and all pages import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
