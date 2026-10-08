from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from utils.config import get_api_base_url


class APIClientError(RuntimeError):
    """Raised when the Streamlit UI cannot reach or parse the backend API."""


class APIClient:
    """Small HTTP client that consumes the FastAPI REST endpoints only."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or get_api_base_url()).rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, path: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": 10.0}
        if self.token:
            kwargs["headers"] = self._headers()
        try:
            response = requests.get(f"{self.base_url}{path}", **kwargs)
        except requests.Timeout:
            raise APIClientError(
                "The API request timed out. Please try again."
            ) from None
        except requests.RequestException:
            raise APIClientError(
                "The API could not be reached. Please try again."
            ) from None

        if response.status_code >= 400:
            raise APIClientError(
                f"API request failed (HTTP {response.status_code}). Please try again."
            )

        try:
            payload = response.json()
        except ValueError:
            raise APIClientError("The API returned an invalid response.") from None
        if not isinstance(payload, dict):
            raise APIClientError("The API returned an invalid response.")
        return payload

    def _request_list(self, path: str) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"timeout": 10.0}
        if self.token:
            kwargs["headers"] = self._headers()
        try:
            response = requests.get(f"{self.base_url}{path}", **kwargs)
        except requests.Timeout:
            raise APIClientError(
                "The API request timed out. Please try again."
            ) from None
        except requests.RequestException:
            raise APIClientError(
                "The API could not be reached. Please try again."
            ) from None

        if response.status_code >= 400:
            raise APIClientError(
                f"API request failed (HTTP {response.status_code}). Please try again."
            )

        try:
            payload = response.json()
        except ValueError:
            raise APIClientError("The API returned an invalid response.") from None
        if not isinstance(payload, list):
            raise APIClientError("The API returned an invalid response.")
        return payload

    def _post(
        self, path: str, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"json": json_data, "timeout": 20.0}
        if self.token:
            kwargs["headers"] = self._headers()
        try:
            response = requests.post(f"{self.base_url}{path}", **kwargs)
        except requests.Timeout:
            raise APIClientError(
                "The API request timed out. Please try again."
            ) from None
        except requests.RequestException:
            raise APIClientError(
                "The API could not be reached. Please try again."
            ) from None

        if response.status_code >= 400:
            raise APIClientError(
                f"API request failed (HTTP {response.status_code}). Please try again."
            )

        try:
            payload = response.json()
        except ValueError:
            raise APIClientError("The API returned an invalid response.") from None
        if not isinstance(payload, dict):
            raise APIClientError("The API returned an invalid response.")
        return payload

    def _delete(self, path: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": 10.0}
        if self.token:
            kwargs["headers"] = self._headers()
        try:
            response = requests.delete(f"{self.base_url}{path}", **kwargs)
        except requests.Timeout:
            raise APIClientError(
                "The API request timed out. Please try again."
            ) from None
        except requests.RequestException:
            raise APIClientError(
                "The API could not be reached. Please try again."
            ) from None

        if response.status_code >= 400:
            raise APIClientError(
                f"API request failed (HTTP {response.status_code}). Please try again."
            )

        try:
            payload = response.json()
        except ValueError:
            raise APIClientError("The API returned an invalid response.") from None
        if not isinstance(payload, dict):
            raise APIClientError("The API returned an invalid response.")
        return payload

    def get_health(self) -> dict[str, Any]:
        return self._request("/health")

    def get_player_profile(self, game_name: str, tag_line: str) -> dict[str, Any]:
        payload = self._request(
            f"/players/{quote(game_name, safe='')}/{quote(tag_line, safe='')}"
        )
        if not payload.get("puuid") and not (
            isinstance(payload.get("game_name"), str)
            and payload["game_name"].strip()
            and isinstance(payload.get("tag_line"), str)
            and payload["tag_line"].strip()
        ):
            raise APIClientError("The API returned an invalid player profile.")
        return payload

    def get_player_rank(self, game_name: str, tag_line: str) -> dict[str, Any]:
        payload = self._request(
            f"/players/{quote(game_name, safe='')}/{quote(tag_line, safe='')}/rank"
        )
        if (
            not isinstance(payload.get("tier_name"), str)
            or not payload["tier_name"].strip()
        ):
            raise APIClientError("The API returned an invalid rank response.")
        return payload

    def get_player_matches(self, game_name: str, tag_line: str) -> dict[str, Any]:
        payload = self._request(
            f"/players/{quote(game_name, safe='')}/{quote(tag_line, safe='')}/matches"
        )
        matches = payload.get("matches")
        display_fields = {
            "map_name",
            "mode",
            "result",
            "kills",
            "deaths",
            "assists",
            "agent_name",
        }
        if not isinstance(matches, list) or any(
            not isinstance(match, dict) or not display_fields <= match.keys()
            for match in matches
        ):
            raise APIClientError("The API returned an invalid match history.")
        return payload

    def get_player_stats(self, game_name: str, tag_line: str) -> dict[str, Any]:
        payload = self._request(
            f"/players/{quote(game_name, safe='')}/{quote(tag_line, safe='')}/stats"
        )
        if not isinstance(payload, dict):
            raise APIClientError("The API returned an invalid stats overview.")
        return payload

    def generate_coaching_report(
        self,
        game_name: str,
        tag_line: str,
        *,
        region: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        query = f"?limit={limit}" + (f"&region={region}" if region else "")
        return self._post(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/reports{query}"
        )

    def list_coaching_reports(
        self,
        game_name: str,
        tag_line: str,
        *,
        limit: int = 10,
    ) -> dict[str, Any]:
        return self._request(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/reports?limit={limit}"
        )

    def get_coaching_report(
        self,
        game_name: str,
        tag_line: str,
        report_id: str,
    ) -> dict[str, Any]:
        return self._request(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/reports/{quote(report_id, safe='')}"
        )

    def invalidate_cache(
        self,
        game_name: str,
        tag_line: str,
    ) -> dict[str, Any]:
        return self._delete(
            f"/players/{quote(game_name, safe='')}/" f"{quote(tag_line, safe='')}/cache"
        )

    def register(self, email: str, password: str) -> dict[str, Any]:
        return self._post("/auth/register", {"email": email, "password": password})

    def login(self, email: str, password: str) -> dict[str, Any]:
        payload = self._post("/auth/login", {"email": email, "password": password})
        if "access_token" in payload:
            self.token = payload["access_token"]
        return payload

    def get_me(self) -> dict[str, Any]:
        return self._request("/auth/me")

    def link_account(
        self,
        game_name: str,
        tag_line: str,
        *,
        region: str | None = None,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        return self._post(
            "/auth/me/accounts",
            {
                "game_name": game_name,
                "tag_line": tag_line,
                "region": region,
                "is_primary": is_primary,
            },
        )

    def list_linked_accounts(self) -> list[dict[str, Any]]:
        return self._request_list("/auth/me/accounts")

    def delete_linked_account(self, account_id: str) -> dict[str, Any]:
        return self._delete(f"/auth/me/accounts/{quote(account_id, safe='')}")

    def get_player_progression(self, game_name: str, tag_line: str) -> dict[str, Any]:
        return self._request(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/progression"
        )

    def sync_player(
        self, game_name: str, tag_line: str, *, region: str | None = None
    ) -> dict[str, Any]:
        query = f"?region={region}" if region else ""
        return self._post(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/sync{query}"
        )

    def analyze_scoreboard(
        self,
        image_base64: str,
        *,
        game_name: str | None = None,
        tag_line: str | None = None,
        save_to_history: bool = True,
    ) -> dict[str, Any]:
        return self._post(
            "/vision/scoreboard/analyze",
            {
                "image_base64": image_base64,
                "game_name": game_name,
                "tag_line": tag_line,
                "save_to_history": save_to_history,
            },
        )

    def get_match_timeline(
        self, match_id: str, *, player: str | None = None
    ) -> dict[str, Any]:
        query = f"?player={quote(player, safe='')}" if player else ""
        return self._request(f"/matches/{quote(match_id, safe='')}/timeline{query}")

    def get_player_timeline_analytics(
        self,
        game_name: str,
        tag_line: str,
        *,
        region: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        params = [f"limit={limit}"]
        if region:
            params.append(f"region={quote(region, safe='')}")
        query = f"?{'&'.join(params)}"
        return self._request(
            f"/players/{quote(game_name, safe='')}/"
            f"{quote(tag_line, safe='')}/timeline-analytics{query}"
        )


def get_api_client() -> APIClient:
    return APIClient()
