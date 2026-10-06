from __future__ import annotations

import os
from typing import Final

import streamlit as st

DEFAULT_API_BASE_URL: Final[str] = "http://127.0.0.1:8000"
API_BASE_URL_KEY: Final[str] = "VALORANT_API_BASE_URL"


def _from_streamlit_secrets() -> str | None:
    """Return the configured base URL from Streamlit secrets, if available.

    Streamlit Community Cloud injects configuration through ``st.secrets``.
    Accessing it raises when no secrets file exists, so the lookup is guarded
    to keep local execution without secrets working exactly as before.
    """
    try:
        value = st.secrets.get(API_BASE_URL_KEY)
    except Exception:  # noqa: BLE001 - secrets are optional at runtime
        return None
    return str(value) if value else None


def get_api_base_url() -> str:
    """Return the backend base URL configured for the Streamlit demo.

    Resolution order: Streamlit secrets, environment variable, local default.
    """
    return (
        _from_streamlit_secrets()
        or os.getenv(API_BASE_URL_KEY)
        or DEFAULT_API_BASE_URL
    ).rstrip("/")
