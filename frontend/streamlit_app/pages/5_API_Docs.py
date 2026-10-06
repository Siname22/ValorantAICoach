from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _bootstrap  # noqa: E402, F401

from components.sections import render_api_docs_page  # noqa: E402

render_api_docs_page()
