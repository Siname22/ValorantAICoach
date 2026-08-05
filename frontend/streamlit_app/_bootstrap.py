"""Import bootstrap shared by the Streamlit entrypoint and its pages.

Streamlit adds the main script directory to ``sys.path`` when the app starts,
but that behaviour is not guaranteed for every execution context (Streamlit
Community Cloud runs the app from the repository root, and page scripts may be
imported before the entrypoint finishes bootstrapping). Importing this module
first makes ``components`` and ``utils`` resolvable in all cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def ensure_app_on_path() -> Path:
    """Register the Streamlit app directory on ``sys.path`` and return it."""
    app_dir = str(APP_DIR)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    return APP_DIR


ensure_app_on_path()
