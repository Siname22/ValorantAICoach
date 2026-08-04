"""Google AI Studio (Gemini) client used by the AI Coach chat page.

The module mirrors the structure already used by :mod:`utils.api_client`: a
dedicated error type, a thin wrapper class, and a small factory function. All
Gemini specifics stay here so the Streamlit page only deals with presentation.

Two design decisions are worth calling out:

* **The official SDK is** ``google-genai``. The older ``google-generativeai``
  package was deprecated on 30 November 2025 and is no longer maintained, so it
  is intentionally not used here.
* **The import is lazy and guarded.** If the dependency is missing, the page
  renders a setup message instead of crashing the whole Streamlit app, which
  keeps the already-deployed pages working no matter what.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Final

import streamlit as st

API_KEY_SECRET: Final[str] = "GEMINI_API_KEY"
MODEL_SECRET: Final[str] = "GEMINI_MODEL"

#: Accepted previously and still honoured, so an existing deployment configured
#: with the Google-branded name keeps working after the rename.
LEGACY_API_KEY_SECRET: Final[str] = "GOOGLE_API_KEY"

#: Stable model as of August 2026. ``gemini-2.0-flash`` is already shut down and
#: ``gemini-2.5-flash`` reaches end of life in October 2026, so the default
#: targets the current stable Gemini 3 Flash generation.
DEFAULT_MODEL: Final[str] = "gemini-3.5-flash"

#: Conversation turns kept when rebuilding the Gemini history. Bounding it keeps
#: latency and token usage predictable during a live demo.
MAX_HISTORY_TURNS: Final[int] = 20

ROLE_USER: Final[str] = "user"
ROLE_ASSISTANT: Final[str] = "assistant"
_GEMINI_MODEL_ROLE: Final[str] = "model"


class GeminiClientError(RuntimeError):
    """Raised when the Streamlit UI cannot reach or use the Gemini API."""


class GeminiConfigurationError(GeminiClientError):
    """Raised when the API key or the SDK dependency is not available."""


@dataclass(frozen=True)
class ChatMessage:
    """A single conversation turn, stored in ``st.session_state``.

    Using ``assistant`` as the role (instead of Gemini's ``model``) keeps the
    structure aligned with ``st.chat_message``; the translation to the SDK
    vocabulary happens in :meth:`GeminiCoachClient.send_message`.
    """

    role: str
    content: str


def _read_setting(key: str) -> str | None:
    """Return a configuration value from Streamlit secrets or the environment.

    Accessing ``st.secrets`` raises when no secrets file exists, so the lookup
    is guarded to keep local execution without secrets working.
    """
    try:
        value = st.secrets.get(key)
    except Exception:  # noqa: BLE001 - secrets are optional at runtime
        value = None
    return str(value) if value else os.getenv(key)


def get_api_key() -> str | None:
    """Return the configured Google AI Studio API key, if any.

    ``GEMINI_API_KEY`` is the documented name. ``GOOGLE_API_KEY`` is still read
    as a fallback so already-configured environments do not break.
    """
    for name in (API_KEY_SECRET, LEGACY_API_KEY_SECRET):
        key = _read_setting(name)
        if key and key.strip():
            return key.strip()
    return None


def get_model_name() -> str:
    """Return the Gemini model to use, allowing an override via secrets."""
    return _read_setting(MODEL_SECRET) or DEFAULT_MODEL


def is_configured() -> bool:
    """Return whether the chat can run (SDK installed and key present)."""
    if get_api_key() is None:
        return False
    try:
        import google.genai  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def _import_sdk() -> tuple[Any, Any, Any]:
    """Import the Google GenAI SDK, raising a friendly error when missing."""
    try:
        from google import genai  # noqa: PLC0415
        from google.genai import errors as genai_errors  # noqa: PLC0415
        from google.genai import types as genai_types  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise GeminiConfigurationError(
            "The 'google-genai' package is not installed. Add it to "
            "frontend/streamlit_app/requirements.txt and reinstall the "
            "dependencies."
        ) from exc
    return genai, genai_types, genai_errors


class GeminiCoachClient:
    """Small wrapper around the Gemini chat API for the AI Coach page."""

    def __init__(
        self,
        system_prompt: str,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> None:
        self.system_prompt = system_prompt
        self.model = model or get_model_name()
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        resolved_key = api_key or get_api_key()
        if not resolved_key:
            raise GeminiConfigurationError(
                f"Configura {API_KEY_SECRET} para activar el coach. "
                "Add it to .streamlit/secrets.toml locally, or to the app "
                "secrets in Streamlit Community Cloud."
            )

        self._genai, self._types, self._errors = _import_sdk()
        try:
            self._client = self._genai.Client(api_key=resolved_key)
        except Exception as exc:  # noqa: BLE001 - SDK raises broad errors
            raise GeminiConfigurationError(
                f"Could not initialise the Gemini client: {exc}"
            ) from exc

    def _build_config(self) -> Any:
        return self._types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )

    def _to_sdk_history(self, history: list[ChatMessage]) -> list[Any]:
        """Convert stored messages into the SDK's ``Content`` objects."""
        recent = history[-MAX_HISTORY_TURNS:] if history else []
        contents: list[Any] = []
        for message in recent:
            if not message.content.strip():
                continue
            role = (
                _GEMINI_MODEL_ROLE
                if message.role == ROLE_ASSISTANT
                else ROLE_USER
            )
            contents.append(
                self._types.Content(
                    role=role,
                    parts=[self._types.Part.from_text(text=message.content)],
                )
            )
        return contents

    def send_message(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        """Send ``message`` with the prior ``history`` and return the reply.

        The chat session is rebuilt on every call from the history held in
        ``st.session_state``. That is intentional: Streamlit re-runs the script
        on each interaction, and session state is the single source of truth,
        so no live SDK object needs to survive between runs.
        """
        if not message.strip():
            raise GeminiClientError("The message cannot be empty.")

        try:
            chat = self._client.chats.create(
                model=self.model,
                config=self._build_config(),
                history=self._to_sdk_history(history or []),
            )
            response = chat.send_message(message)
        except self._errors.ClientError as exc:
            raise GeminiClientError(self._explain_client_error(exc)) from exc
        except self._errors.ServerError as exc:
            raise GeminiClientError(
                "Google AI Studio is temporarily unavailable. Please retry in "
                f"a moment. ({exc})"
            ) from exc
        except self._errors.APIError as exc:
            raise GeminiClientError(f"Gemini API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - network/SDK safety net
            raise GeminiClientError(
                f"Unexpected error while contacting Gemini: {exc}"
            ) from exc

        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise GeminiClientError(
                "Gemini returned an empty response. This usually means the "
                "answer was blocked by a safety filter or the token limit was "
                "reached. Try rephrasing your question."
            )
        return text.strip()

    @staticmethod
    def _explain_client_error(exc: Exception) -> str:
        """Translate a 4xx SDK error into an actionable message."""
        detail = str(exc)
        lowered = detail.lower()
        if "api key" in lowered or "api_key" in lowered or "401" in lowered:
            return (
                "The Google AI Studio API key was rejected. Check the value of "
                f"'{API_KEY_SECRET}' in your Streamlit secrets."
            )
        if "quota" in lowered or "429" in lowered or "resource_exhausted" in lowered:
            return (
                "The Gemini free-tier quota has been exhausted. Wait for the "
                "quota window to reset or use a different API key."
            )
        if "not found" in lowered or "404" in lowered:
            return (
                f"The model '{get_model_name()}' is not available for this API "
                f"key. Override it with the '{MODEL_SECRET}' secret."
            )
        return f"Gemini rejected the request: {detail}"


def get_gemini_client(
    system_prompt: str,
    model: str | None = None,
) -> GeminiCoachClient:
    """Return a ready-to-use coach client for the given system prompt."""
    return GeminiCoachClient(system_prompt=system_prompt, model=model)


# ---------------------------------------------------------------------------
# Forward-looking hooks: Streamlit -> Gemini -> knowledge -> FastAPI / Tracker
# ---------------------------------------------------------------------------
# The functions below are the seam for the next milestone. They deliberately do
# not call the backend yet, as required by the current scope: the chat must stay
# independent from the Tracker integration. Each one already returns the exact
# shape that `coach_persona.build_system_prompt(player_context=...)` expects, so
# enabling personalised coaching later is a matter of filling in the bodies with
# `utils.api_client.get_api_client()` calls, without touching the chat page.


def format_player_context(
    profile: dict[str, Any] | None = None,
    rank: dict[str, Any] | None = None,
    matches: dict[str, Any] | None = None,
) -> str | None:
    """Render backend payloads into a compact context block for the prompt.

    Returns ``None`` when no data is supplied, which makes the coach fall back
    to general knowledge instead of inventing statistics.
    """
    sections: list[str] = []
    if profile:
        sections.append(f"## Player profile\n{_as_bullets(profile)}")
    if rank:
        sections.append(f"## Competitive rank\n{_as_bullets(rank)}")
    if matches:
        sections.append(f"## Recent matches\n{_as_bullets(matches)}")
    return "\n\n".join(sections) if sections else None


def _as_bullets(payload: dict[str, Any]) -> str:
    """Flatten a shallow payload into readable ``- key: value`` lines."""
    lines = []
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"- {key}: {value!r}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def fetch_player_context(game_name: str, tag_line: str) -> str | None:
    """Placeholder for the future FastAPI-backed personalisation step.

    Intended implementation once the integration is approved::

        client = get_api_client()
        return format_player_context(
            profile=client.get_player_profile(game_name, tag_line),
            rank=client.get_player_rank(game_name, tag_line),
            matches=client.get_player_matches(game_name, tag_line),
        )

    It stays disabled on purpose so the chatbot never depends on the backend
    being reachable from Streamlit Community Cloud.
    """
    return None
