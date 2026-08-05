from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Community Cloud launches the app from the repository root, so the
# directory holding this file is not guaranteed to be importable. Registering it
# explicitly keeps `components` and `utils` resolvable in every environment.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components.sections import render_home_page  # noqa: E402

render_home_page()
