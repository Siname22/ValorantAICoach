from __future__ import annotations

from typing import Any

import requests

from utils.config import get_api_base_url


class APIClientError(RuntimeError):
    """Raised when the Streamlit UI cannot reach or parse the backend API."""


class APIClient:
    """Small HTTP client that consumes the FastAPI REST endpoints only."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_api_base_url()).rstrip("/")

    def _request(self, path: str) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}{path}", timeout=10.0)
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text)
            raise APIClientError(f"API request failed: {detail}")
        return response.json()

    def get_health(self) -> dict[str, Any]:
        return self._request("/health")

    def get_player_profile(self, game_name: str, tag_line: str) -> dict[str, Any]:
        return self._request(f"/players/{game_name}/{tag_line}")

    def get_player_rank(self, game_name: str, tag_line: str) -> dict[str, Any]:
        return self._request(f"/players/{game_name}/{tag_line}/rank")

    def get_player_matches(self, game_name: str, tag_line: str) -> dict[str, Any]:
        return self._request(f"/players/{game_name}/{tag_line}/matches")


def get_api_client() -> APIClient:
    return APIClient()
