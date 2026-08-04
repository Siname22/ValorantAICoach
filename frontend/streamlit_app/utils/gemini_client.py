"""Google AI Studio (Gemini) client used by the AI Coach chat page.

The module mirrors the structure already used by :mod:`utils.api_client`: a
dedicated error type, a thin wrapper class, and a small factory function. All
Gemini specifics stay here so the Streamlit page only deals with presentation.

Design decisions worth calling out:

* **The official SDK is** ``google-genai``. The older ``google-generativeai``
  package was deprecated on 30 November 2025 and is no longer maintained, so it
  is intentionally not used here.
* **The import is lazy and guarded.** If the dependency is missing, the page
  renders a setup message instead of crashing the whole Streamlit app, which
  keeps the already-deployed pages working no matter what.
* **Resilience is layered.** A public demo cannot depend on a single model being
  healthy, so transient failures are absorbed by two mechanisms that compose:
  bounded retries with incremental backoff for the *same* model, and an
  automatic switch to the next model in :data:`MODEL_CHAIN` when a model stays
  unavailable. Only when every option is exhausted does the user see a message,
  and that message is always human-readable Spanish, never a stack trace or the
  raw JSON returned by Google.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Final

import streamlit as st

logger = logging.getLogger(__name__)

API_KEY_SECRET: Final[str] = "GEMINI_API_KEY"
MODEL_SECRET: Final[str] = "GEMINI_MODEL"

#: Accepted previously and still honoured, so an existing deployment configured
#: with the Google-branded name keeps working after the rename.
LEGACY_API_KEY_SECRET: Final[str] = "GOOGLE_API_KEY"

#: Primary model. ``gemini-2.5-flash`` is Google's price-performance workhorse
#: for low-latency, high-volume chat traffic, which is exactly this workload.
DEFAULT_MODEL: Final[str] = "gemini-2.5-flash"

#: Ordered fallback chain, tried left to right whenever a model reports itself
#: as unavailable or rate limited. ``-lite`` sits second because it serves the
#: same family with a larger capacity headroom, and the Gemini 3 stable release
#: closes the chain as a last resort from a different serving pool.
MODEL_CHAIN: Final[tuple[str, ...]] = (
    DEFAULT_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
)

#: Attempts per model before moving on. Three is enough to ride out the short
#: capacity spikes that cause 503s without keeping the user waiting.
MAX_ATTEMPTS_PER_MODEL: Final[int] = 3

#: Seconds waited before each retry of the same model (incremental backoff).
RETRY_BACKOFF_SECONDS: Final[tuple[float, ...]] = (1.0, 2.0)

#: HTTP statuses that mean "try again elsewhere" rather than "the request is
#: wrong". 503 is the high-demand case reported in production; 429 is quota
#: pressure; 500 and 504 are transient upstream faults.
TRANSIENT_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})

#: Conversation turns kept when rebuilding the Gemini history. Bounding it keeps
#: latency and token usage predictable during a live demo.
MAX_HISTORY_TURNS: Final[int] = 20

ROLE_USER: Final[str] = "user"
ROLE_ASSISTANT: Final[str] = "assistant"
_GEMINI_MODEL_ROLE: Final[str] = "model"

# ---------------------------------------------------------------------------
# User-facing copy
# ---------------------------------------------------------------------------
# Every message the chat can display lives here, in Spanish, written for a
# non-technical audience. Keeping them as named constants means the UI never
# interpolates an exception into the page, which is what previously leaked
# "503 UNAVAILABLE ... high demand" to the user.

#: Transient exhaustion: every model in the chain reported saturation or rate
#: limiting. Deliberately free of status codes, provider names and emoji, so the
#: string can be asserted verbatim in the test suite.
MSG_OVERLOADED: Final[str] = (
    "El servicio de IA está temporalmente saturado. "
    "Inténtalo de nuevo en unos segundos."
)

#: Permanent configuration fault: credential rejected, insufficient permissions,
#: or no reachable model. The wording avoids naming the secret so a screenshot of
#: the deployed app never hints at the credential layout.
MSG_CONFIG_REVIEW: Final[str] = (
    "La configuración del servicio de IA necesita revisión."
)

#: Kept as an alias because both an invalid key and an unavailable model are, from
#: the user's point of view, the same actionable situation: configuration.
MSG_INVALID_KEY: Final[str] = MSG_CONFIG_REVIEW
MSG_MODEL_UNAVAILABLE: Final[str] = MSG_CONFIG_REVIEW

#: Shown by the page itself, before any client is built, when no key is present.
MSG_MISSING_KEY: Final[str] = (
    f"Configura {API_KEY_SECRET} para activar el coach."
)

#: Unclassified failure. Anything that is neither transient nor a configuration
#: problem lands here, so the user always gets an actionable sentence instead of
#: a traceback.
MSG_UNEXPECTED: Final[str] = (
    "El coach tuvo un problema inesperado. Inténtalo de nuevo."
)
MSG_GENERIC_FAILURE: Final[str] = MSG_UNEXPECTED

#: Content-level outcomes, distinct from outages: the model answered with nothing
#: usable, or the user submitted an empty prompt.
MSG_EMPTY_RESPONSE: Final[str] = (
    "El coach no ha podido formular una respuesta para esa pregunta. "
    "Prueba a reformularla de otra manera."
)
MSG_EMPTY_MESSAGE: Final[str] = (
    "Escribe una pregunta para que el coach pueda ayudarte."
)
MSG_SDK_MISSING: Final[str] = (
    "Falta la dependencia 'google-genai'. Añádela a "
    "frontend/streamlit_app/requirements.txt y reinstala las dependencias."
)


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
    """Return the model the chat will try first.

    The ``GEMINI_MODEL`` secret takes precedence, so the deployed app can be
    pointed at a different model from the Streamlit Cloud settings panel without
    touching the code.
    """
    return _read_setting(MODEL_SECRET) or DEFAULT_MODEL


def get_model_chain(model: str | None = None) -> tuple[str, ...]:
    """Return the ordered list of models to try, honouring the override.

    The configured model always comes first; the remaining entries of
    :data:`MODEL_CHAIN` follow as fallbacks, de-duplicated so an override that
    already belongs to the chain does not get attempted twice.
    """
    preferred = model or get_model_name()
    chain: list[str] = [preferred]
    for candidate in MODEL_CHAIN:
        if candidate not in chain:
            chain.append(candidate)
    return tuple(chain)


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
        raise GeminiConfigurationError(MSG_SDK_MISSING) from exc
    return genai, genai_types, genai_errors


def _status_code(exc: Exception) -> int | None:
    """Best-effort extraction of the HTTP status carried by an SDK error.

    ``APIError`` exposes ``.code``, which is far more reliable than matching
    substrings in the message. The textual check is kept only as a safety net
    for transport-level failures that never reach the SDK error hierarchy.
    """
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status
    return None


def _is_transient(exc: Exception) -> bool:
    """Return whether the failure justifies a retry or a model switch."""
    code = _status_code(exc)
    if code in TRANSIENT_STATUS_CODES:
        return True
    # Network-level problems never carry an HTTP status, so they are matched by
    # exception type before falling back to message inspection.
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    lowered = str(exc).lower()
    markers = (
        "unavailable",
        "overloaded",
        "high demand",
        "resource_exhausted",
        "rate limit",
        "deadline",
        "timeout",
        "timed out",
        "try again",
        "temporarily",
        "connection reset",
        "connection aborted",
    )
    return any(marker in lowered for marker in markers)


def _is_model_missing(exc: Exception) -> bool:
    """Return whether the model itself was rejected as unknown."""
    if _status_code(exc) == 404:
        return True
    lowered = str(exc).lower()
    return "not found" in lowered or "does not exist" in lowered


def _is_auth_failure(exc: Exception) -> bool:
    """Return whether the credential was rejected."""
    if _status_code(exc) in {401, 403}:
        return True
    lowered = str(exc).lower()
    return (
        "api key" in lowered
        or "api_key" in lowered
        or "permission_denied" in lowered
        or "unauthenticated" in lowered
    )


class GeminiCoachClient:
    """Small wrapper around the Gemini chat API for the AI Coach page."""

    def __init__(
        self,
        system_prompt: str,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
        sleep: Any = time.sleep,
    ) -> None:
        self.system_prompt = system_prompt
        self.model = model or get_model_name()
        self.model_chain = get_model_chain(self.model)
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        #: Model that answered the last successful call, so the UI can show
        #: which one is actually serving the conversation after a fallback.
        self.active_model = self.model
        self._sleep = sleep

        resolved_key = api_key or get_api_key()
        if not resolved_key:
            raise GeminiConfigurationError(MSG_MISSING_KEY)

        self._genai, self._types, self._errors = _import_sdk()
        try:
            self._client = self._genai.Client(api_key=resolved_key)
        except Exception as exc:  # noqa: BLE001 - SDK raises broad errors
            logger.error("Gemini client initialisation failed: %s", exc)
            raise GeminiConfigurationError(MSG_INVALID_KEY) from exc

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

    def _call_model(
        self,
        model: str,
        message: str,
        history: list[ChatMessage],
    ) -> str:
        """Send one request to ``model`` and return the extracted reply text."""
        chat = self._client.chats.create(
            model=model,
            config=self._build_config(),
            history=self._to_sdk_history(history),
        )
        response = chat.send_message(message)
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise GeminiClientError(MSG_EMPTY_RESPONSE)
        return text.strip()

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

        Resilience works in two nested loops. For each model in
        :data:`MODEL_CHAIN`, up to :data:`MAX_ATTEMPTS_PER_MODEL` attempts are
        made with incremental backoff; if the model is still unavailable, the
        next one takes over. Authentication failures break out immediately,
        because retrying a rejected key only wastes the user's time.
        """
        if not message.strip():
            raise GeminiClientError(MSG_EMPTY_MESSAGE)

        turns = history or []
        last_transient: Exception | None = None
        model_rejected = False

        for model in self.model_chain:
            for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
                try:
                    reply = self._call_model(model, message, turns)
                except GeminiClientError:
                    # Empty response: a content-level outcome, not an outage.
                    raise
                except Exception as exc:  # noqa: BLE001 - classified below
                    if _is_auth_failure(exc):
                        logger.error(
                            "Gemini rejected the credential (model=%s): %s",
                            model,
                            exc,
                        )
                        raise GeminiConfigurationError(MSG_INVALID_KEY) from exc

                    if _is_model_missing(exc):
                        logger.warning(
                            "Model '%s' is not available for this key: %s",
                            model,
                            exc,
                        )
                        model_rejected = True
                        last_transient = exc
                        break  # No point retrying an unknown model.

                    if _is_transient(exc):
                        last_transient = exc
                        logger.warning(
                            "Transient Gemini failure (model=%s, attempt=%d/%d, "
                            "status=%s): %s",
                            model,
                            attempt,
                            MAX_ATTEMPTS_PER_MODEL,
                            _status_code(exc),
                            exc,
                        )
                        if attempt < MAX_ATTEMPTS_PER_MODEL:
                            index = min(
                                attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1
                            )
                            self._sleep(RETRY_BACKOFF_SECONDS[index])
                            continue
                        break  # Exhausted this model; fall through to the next.

                    logger.error(
                        "Unexpected Gemini failure (model=%s): %s", model, exc
                    )
                    raise GeminiClientError(MSG_GENERIC_FAILURE) from exc
                else:
                    if model != self.model:
                        logger.info(
                            "Gemini fallback succeeded: '%s' answered after "
                            "'%s' was unavailable.",
                            model,
                            self.model,
                        )
                    self.active_model = model
                    return reply

        logger.error(
            "Every Gemini model in the chain failed: %s", list(self.model_chain)
        )
        if model_rejected and not _is_transient(last_transient or Exception()):
            raise GeminiClientError(MSG_MODEL_UNAVAILABLE) from last_transient
        raise GeminiClientError(MSG_OVERLOADED) from last_transient


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
