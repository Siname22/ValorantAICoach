"""Resilience test suite for the Gemini-backed AI Coach client.

The suite covers the five scenarios required by the hardening specification:

1. No ``GEMINI_API_KEY`` configured.
2. A rejected (fake) API key.
3. A saturated model returning ``503``.
4. An empty reply from the model.
5. A network timeout.

Two design decisions make this suite safe to run anywhere, including CI:

* **The Gemini API is never contacted.** A test double replicates the surface of
  ``google.genai.Client`` that the production code actually uses
  (``chats.create`` and ``send_message``), so failures can be provoked
  deterministically without consuming quota or requiring a real credential.
* **Backoff is injected, not patched globally.** ``GeminiCoachClient`` accepts a
  ``sleep`` callable, so the suite records the requested delays and asserts the
  exact backoff schedule instead of waiting several real seconds.

Run it from the repository root::

    python frontend/streamlit_app/tests/test_gemini_resilience.py

The script exits with status ``0`` when every check passes and ``1`` otherwise,
which makes it usable as a pre-deployment gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# The suite must run from the repository root, mirroring how Streamlit Community
# Cloud starts the app, so the app directory is registered explicitly.
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

# Any inherited credential would make the "missing key" scenario pass for the
# wrong reason, so the environment is cleaned before the module is imported.
for _leaked in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"):
    os.environ.pop(_leaked, None)

from utils import gemini_client as gc  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal assertion harness
# ---------------------------------------------------------------------------

_PASSED = 0
_FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    """Record the outcome of a single assertion."""
    global _PASSED
    if condition:
        _PASSED += 1
        print(f"  [OK]   {label}")
    else:
        _FAILED.append(label)
        suffix = f" -> {detail}" if detail else ""
        print(f"  [FAIL] {label}{suffix}")


def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeAPIError(Exception):
    """Stand-in for ``google.genai.errors.APIError``.

    The production classifier reads ``.code``, so the double exposes the same
    attribute. This is precisely why the classifier does not match substrings:
    the behaviour is driven by the numeric status, independent of the wording.
    """

    def __init__(self, code: int, message: str = "simulated failure") -> None:
        super().__init__(message)
        self.code = code
        self.status = code


class FakeResponse:
    def __init__(self, text: Any) -> None:
        self.text = text


class FakeChat:
    def __init__(self, model: str, outcomes: dict[str, list[Any]]) -> None:
        self._model = model
        self._outcomes = outcomes

    def send_message(self, message: str) -> FakeResponse:
        queue = self._outcomes.get(self._model)
        if queue is None:
            # Any model without a scripted outcome answers normally, which keeps
            # each scenario focused on the model under test.
            return FakeResponse(f"Respuesta de {self._model}")
        outcome = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class FakeChats:
    def __init__(self, outcomes: dict[str, list[Any]], calls: list[str]) -> None:
        self._outcomes = outcomes
        self._calls = calls

    def create(self, model: str, config: Any, history: Any) -> FakeChat:
        self._calls.append(model)
        return FakeChat(model, self._outcomes)


class FakeClient:
    def __init__(self, outcomes: dict[str, list[Any]], calls: list[str]) -> None:
        self.chats = FakeChats(outcomes, calls)


def build_client(
    outcomes: dict[str, list[Any]],
    api_key: str = "test-key",
) -> tuple[gc.GeminiCoachClient, list[str], list[float]]:
    """Return a client wired to the doubles, plus its call and sleep journals."""
    calls: list[str] = []
    sleeps: list[float] = []

    client = gc.GeminiCoachClient.__new__(gc.GeminiCoachClient)
    client.system_prompt = "system prompt for testing"
    client.model = gc.DEFAULT_MODEL
    client.model_chain = gc.get_model_chain(gc.DEFAULT_MODEL)
    client.temperature = 0.7
    client.max_output_tokens = 1024
    client.active_model = gc.DEFAULT_MODEL
    client._sleep = sleeps.append
    client._client = FakeClient(outcomes, calls)
    client._genai = None
    client._errors = None
    client._types = _FakeTypes()
    return client, calls, sleeps


class _FakePart:
    @staticmethod
    def from_text(text: str) -> dict[str, str]:
        return {"text": text}


class _FakeTypes:
    """Replaces ``google.genai.types`` for history and config construction."""

    Part = _FakePart

    @staticmethod
    def Content(role: str, parts: Any) -> dict[str, Any]:  # noqa: N802
        return {"role": role, "parts": parts}

    @staticmethod
    def GenerateContentConfig(**kwargs: Any) -> dict[str, Any]:  # noqa: N802
        return kwargs


# ---------------------------------------------------------------------------
# Case 1 - no GEMINI_API_KEY configured
# ---------------------------------------------------------------------------


def case_1_missing_key() -> None:
    section("Case 1 - GEMINI_API_KEY not configured")

    check(
        "get_api_key() returns None with no credential present",
        gc.get_api_key() is None,
    )
    check(
        "is_configured() reports the chat as unavailable",
        gc.is_configured() is False,
    )
    check(
        "the notice text matches the specification verbatim",
        gc.MSG_MISSING_KEY == "Configura GEMINI_API_KEY para activar el coach.",
        gc.MSG_MISSING_KEY,
    )

    try:
        gc.GeminiCoachClient(system_prompt="p", api_key=None)
    except gc.GeminiConfigurationError as exc:
        check(
            "building a client raises a configuration error, not a crash",
            str(exc) == gc.MSG_MISSING_KEY,
            str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        check("building a client raises GeminiConfigurationError", False, repr(exc))
    else:
        check("building a client without a key must fail", False)

    # The page must stay renderable: the notice is a warning, never an exception
    # that would break the Streamlit run and take the whole app down.
    check(
        "GeminiConfigurationError derives from GeminiClientError",
        issubclass(gc.GeminiConfigurationError, gc.GeminiClientError),
    )


# ---------------------------------------------------------------------------
# Case 2 - rejected API key
# ---------------------------------------------------------------------------


def case_2_invalid_key() -> None:
    section("Case 2 - rejected API key")

    for code in (401, 403):
        client, calls, sleeps = build_client(
            {gc.DEFAULT_MODEL: [FakeAPIError(code, "API key not valid")]}
        )
        try:
            client.send_message("¿Cómo mejoro mi aim?")
        except gc.GeminiConfigurationError as exc:
            check(
                f"HTTP {code} produces the configuration message",
                str(exc) == "La configuración del servicio de IA necesita revisión.",
                str(exc),
            )
            check(
                f"HTTP {code} is not retried (single attempt)",
                len(calls) == 1 and sleeps == [],
                f"calls={calls}, sleeps={sleeps}",
            )
            check(
                f"HTTP {code} message leaks no status code",
                "401" not in str(exc) and "403" not in str(exc),
                str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            check(f"HTTP {code} raises GeminiConfigurationError", False, repr(exc))
        else:
            check(f"HTTP {code} must not succeed", False)

    check(
        "the classifier flags 401/403 as authentication failures",
        gc._is_auth_failure(FakeAPIError(401))
        and gc._is_auth_failure(FakeAPIError(403)),
    )
    check(
        "the classifier does not treat 401/403 as transient",
        not gc._is_transient(FakeAPIError(401))
        and not gc._is_transient(FakeAPIError(403)),
    )


# ---------------------------------------------------------------------------
# Case 3 - saturated model (503)
# ---------------------------------------------------------------------------


def case_3_model_overloaded() -> None:
    section("Case 3 - saturated model (503)")

    overload = "503 UNAVAILABLE. This model is currently experiencing high demand."

    # 3a. The primary model is saturated; the fallback answers.
    client, calls, sleeps = build_client(
        {gc.DEFAULT_MODEL: [FakeAPIError(503, overload)]}
    )
    reply = client.send_message("Me quedo atascado en Plata, ¿qué hago?")

    check(
        "a reply is still delivered to the user",
        bool(reply) and reply.strip() != "",
        repr(reply),
    )
    check(
        "the primary model was attempted three times",
        calls.count(gc.DEFAULT_MODEL) == 3,
        f"calls={calls}",
    )
    check(
        "the backoff schedule is exactly 1s then 2s",
        sleeps == [1.0, 2.0],
        f"sleeps={sleeps}",
    )
    check(
        "the fallback model took over",
        calls[3] == "gemini-2.5-flash-lite",
        f"calls={calls}",
    )
    check(
        "active_model reports the model that actually answered",
        client.active_model == "gemini-2.5-flash-lite",
        client.active_model,
    )
    check(
        "the reply carries no trace of the provider error",
        "503" not in reply and "UNAVAILABLE" not in reply,
        reply,
    )

    # 3b. A transient blip resolves on the second attempt without switching.
    client, calls, sleeps = build_client(
        {gc.DEFAULT_MODEL: [FakeAPIError(503, overload), "Recuperado"]}
    )
    reply = client.send_message("¿Cuándo compro escudo ligero?")
    check(
        "a single transient failure does not change model",
        client.active_model == gc.DEFAULT_MODEL and reply == "Recuperado",
        f"model={client.active_model}, reply={reply!r}",
    )
    check(
        "only one backoff wait was needed",
        sleeps == [1.0],
        f"sleeps={sleeps}",
    )

    # 3c. Every model in the chain is saturated.
    exhausted = {model: [FakeAPIError(503, overload)] for model in gc.MODEL_CHAIN}
    client, calls, sleeps = build_client(exhausted)
    try:
        client.send_message("¿Cómo juego un retake en Ascent?")
    except gc.GeminiClientError as exc:
        message = str(exc)
        check(
            "the exhausted-chain message matches the specification verbatim",
            message
            == "El servicio de IA está temporalmente saturado. "
            "Inténtalo de nuevo en unos segundos.",
            message,
        )
        for forbidden in ("503", "UNAVAILABLE", "high demand", "Traceback", "google"):
            check(
                f"the message never exposes '{forbidden}'",
                forbidden.lower() not in message.lower(),
                message,
            )
        check(
            "every model in the chain was attempted three times",
            len(calls) == 3 * len(gc.MODEL_CHAIN),
            f"calls={len(calls)}",
        )
    except Exception as exc:  # noqa: BLE001
        check("an exhausted chain raises GeminiClientError", False, repr(exc))
    else:
        check("an exhausted chain must not succeed", False)

    # 3d. Rate limiting is transient too, and absorbed the same way.
    client, calls, _ = build_client({gc.DEFAULT_MODEL: [FakeAPIError(429)]})
    reply = client.send_message("¿Qué agente aprendo primero?")
    check(
        "HTTP 429 is absorbed by the fallback",
        client.active_model == "gemini-2.5-flash-lite" and bool(reply),
        client.active_model,
    )

    for code in sorted(gc.TRANSIENT_STATUS_CODES):
        check(
            f"HTTP {code} is classified as transient",
            gc._is_transient(FakeAPIError(code)),
        )


# ---------------------------------------------------------------------------
# Case 4 - empty reply
# ---------------------------------------------------------------------------


def case_4_empty_reply() -> None:
    section("Case 4 - empty reply from the model")

    for label, value in (("None", None), ("empty string", ""), ("blank", "   ")):
        client, _, _ = build_client({gc.DEFAULT_MODEL: [value]})
        try:
            client.send_message("¿Cómo mejoro mi crosshair placement?")
        except gc.GeminiClientError as exc:
            check(
                f"a reply of {label} yields the fallback message",
                str(exc) == gc.MSG_EMPTY_RESPONSE,
                str(exc),
            )
            check(
                f"the {label} message contains no technical detail",
                "None" not in str(exc) and "Traceback" not in str(exc),
                str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            check(f"a reply of {label} raises GeminiClientError", False, repr(exc))
        else:
            check(f"a reply of {label} must not be accepted", False)

    # An empty prompt is rejected before the API is contacted, so no quota is
    # spent on a request that cannot produce anything useful.
    client, calls, _ = build_client({})
    try:
        client.send_message("   ")
    except gc.GeminiClientError as exc:
        check(
            "an empty prompt is rejected with a friendly message",
            str(exc) == gc.MSG_EMPTY_MESSAGE,
            str(exc),
        )
        check("an empty prompt never reaches the API", calls == [], f"calls={calls}")
    else:
        check("an empty prompt must not be sent", False)


# ---------------------------------------------------------------------------
# Case 5 - timeout
# ---------------------------------------------------------------------------


def case_5_timeout() -> None:
    section("Case 5 - network timeout")

    check(
        "TimeoutError is classified as transient",
        gc._is_transient(TimeoutError("connection timed out")),
    )
    check(
        "ConnectionError is classified as transient",
        gc._is_transient(ConnectionError("connection reset by peer")),
    )
    check(
        "a bare TimeoutError with no message is still transient",
        gc._is_transient(TimeoutError()),
    )

    client, calls, sleeps = build_client(
        {gc.DEFAULT_MODEL: [TimeoutError("connection timed out")]}
    )
    reply = client.send_message("¿Cómo tradeo con mi duelista?")
    check(
        "a timeout is retried and then absorbed by the fallback",
        client.active_model == "gemini-2.5-flash-lite" and bool(reply),
        f"model={client.active_model}",
    )
    check(
        "the timeout path applies the same backoff schedule",
        sleeps == [1.0, 2.0],
        f"sleeps={sleeps}",
    )

    # A timeout across the whole chain must still surface as the transient
    # message, never as a raw socket error.
    exhausted = {model: [TimeoutError("timed out")] for model in gc.MODEL_CHAIN}
    client, _, _ = build_client(exhausted)
    try:
        client.send_message("¿Cómo rotar en Split?")
    except gc.GeminiClientError as exc:
        check(
            "a chain-wide timeout reports the transient message",
            str(exc) == gc.MSG_OVERLOADED,
            str(exc),
        )
        check(
            "the timeout message mentions no socket detail",
            "timed out" not in str(exc).lower(),
            str(exc),
        )
    else:
        check("a chain-wide timeout must not succeed", False)


# ---------------------------------------------------------------------------
# Structural guarantees
# ---------------------------------------------------------------------------


def case_6_configuration() -> None:
    section("Configuration and structural guarantees")

    check(
        "the default chain is exactly the specified order",
        gc.MODEL_CHAIN
        == ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"),
        str(gc.MODEL_CHAIN),
    )
    check("three attempts per model", gc.MAX_ATTEMPTS_PER_MODEL == 3)
    check(
        "the backoff constants are 1s and 2s",
        gc.RETRY_BACKOFF_SECONDS == (1.0, 2.0),
        str(gc.RETRY_BACKOFF_SECONDS),
    )
    check(
        "the transient status set matches the specification",
        gc.TRANSIENT_STATUS_CODES == frozenset({429, 500, 502, 503, 504}),
        str(sorted(gc.TRANSIENT_STATUS_CODES)),
    )

    # A custom model must replace only the first position; removing the
    # fallbacks would reintroduce the single-point-of-failure this work removed.
    custom = gc.get_model_chain("gemini-custom")
    check(
        "an override replaces only the first entry",
        custom
        == (
            "gemini-custom",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
        ),
        str(custom),
    )
    check(
        "an override that already belongs to the chain is not duplicated",
        gc.get_model_chain("gemini-2.5-flash-lite")
        == (
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.5-flash",
        ),
        str(gc.get_model_chain("gemini-2.5-flash-lite")),
    )
    check(
        "the chain never contains duplicates",
        len(set(custom)) == len(custom),
    )

    check(
        "404 is treated as an unavailable model, not a transient fault",
        gc._is_model_missing(FakeAPIError(404)) and not gc._is_transient(FakeAPIError(404)),
    )

    # A 404 on every model is a configuration problem, so the user is told to
    # review the configuration rather than to retry pointlessly.
    client, calls, sleeps = build_client(
        {model: [FakeAPIError(404, "model not found")] for model in gc.MODEL_CHAIN}
    )
    try:
        client.send_message("¿Cómo mejoro mi economía?")
    except gc.GeminiClientError as exc:
        check(
            "an unreachable chain reports the configuration message",
            str(exc) == "La configuración del servicio de IA necesita revisión.",
            str(exc),
        )
        check(
            "a 404 is attempted once per model, with no backoff",
            len(calls) == len(gc.MODEL_CHAIN) and sleeps == [],
            f"calls={calls}, sleeps={sleeps}",
        )
    else:
        check("an unreachable chain must not succeed", False)

    # An unclassified fault must not leak either.
    client, _, _ = build_client({gc.DEFAULT_MODEL: [ValueError("internal bug")]})
    try:
        client.send_message("¿Cómo uso las habilidades de Sova?")
    except gc.GeminiClientError as exc:
        check(
            "an unclassified fault reports the unexpected-error message",
            str(exc) == "El coach tuvo un problema inesperado. Inténtalo de nuevo.",
            str(exc),
        )
        check(
            "the unexpected message does not echo the internal cause",
            "internal bug" not in str(exc),
            str(exc),
        )
    else:
        check("an unclassified fault must not succeed", False)


def case_7_persona_and_sdk() -> None:
    section("Persona integrity and SDK compliance")

    from utils.coach_persona import build_system_prompt

    prompt = build_system_prompt()
    check("the system prompt is non-trivial", len(prompt) > 500, str(len(prompt)))

    # The coaching domains required by the brief, in the language of the prompt.
    for topic in (
        "Silver",
        "Platinum",
        "econom",
        "position",
        "trade",
        "agent",
        "map",
        "round",
        "decision",
    ):
        check(
            f"the persona still covers '{topic}'",
            topic.lower() in prompt.lower(),
        )

    check(
        "the prompt forbids inventing statistics",
        "never invent" in prompt.lower() or "do not invent" in prompt.lower(),
    )

    source = (APP_DIR / "utils" / "gemini_client.py").read_text(encoding="utf-8")
    check(
        "the deprecated SDK is never imported",
        "import google.generativeai" not in source
        and "from google.generativeai" not in source,
    )
    check(
        "the current SDK is the one imported",
        "from google import genai" in source,
    )
    check(
        "the API key is never hardcoded",
        "AIza" not in source,
    )

    # Message hygiene: no user-facing constant may carry technical noise.
    user_messages = [
        gc.MSG_OVERLOADED,
        gc.MSG_CONFIG_REVIEW,
        gc.MSG_UNEXPECTED,
        gc.MSG_MISSING_KEY,
        gc.MSG_EMPTY_RESPONSE,
        gc.MSG_EMPTY_MESSAGE,
    ]
    for message in user_messages:
        lowered = message.lower()
        clean = not any(
            token in lowered
            for token in ("503", "429", "unavailable", "traceback", "exception", "google api")
        )
        check(f"the message is free of technical noise: {message[:45]}…", clean, message)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 72)
    print("Gemini AI Coach - resilience test suite")
    print("=" * 72)

    case_1_missing_key()
    case_2_invalid_key()
    case_3_model_overloaded()
    case_4_empty_reply()
    case_5_timeout()
    case_6_configuration()
    case_7_persona_and_sdk()

    total = _PASSED + len(_FAILED)
    print("\n" + "=" * 72)
    print(f"{_PASSED}/{total} comprobaciones superadas")
    if _FAILED:
        print(f"\n{len(_FAILED)} fallo(s):")
        for label in _FAILED:
            print(f"  - {label}")
        return 1
    print("Sin errores.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
