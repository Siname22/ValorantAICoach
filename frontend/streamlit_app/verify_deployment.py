"""Deployment readiness check for the Streamlit frontend.

Simulates how Streamlit Community Cloud loads the app (process launched from the
repository root) and validates that the entrypoint and every page script can be
imported and executed without touching the network.

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


def _check_requirements() -> list[str]:
    """Validate that the root requirements file is parseable and frontend-only."""
    problems: list[str] = []
    requirements = REPO_ROOT / "requirements.txt"
    if not requirements.exists():
        return ["requirements.txt is missing at the repository root"]

    backend_only = {"fastapi", "uvicorn", "sqlalchemy", "alembic", "psycopg"}
    for raw_line in requirements.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("[")[0].split(">")[0].split("=")[0].split("<").pop(0)
        name = name.strip().lower()
        if not name.replace("-", "").replace("_", "").replace(".", "").isalnum():
            problems.append(f"requirements.txt has an invalid entry: {raw_line!r}")
        elif name in backend_only:
            problems.append(f"requirements.txt contains a backend package: {name}")
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

    problems = _check_requirements() + _check_scripts()

    print()
    if problems:
        print("Deployment check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("Deployment check PASSED: entrypoint and all pages import cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
