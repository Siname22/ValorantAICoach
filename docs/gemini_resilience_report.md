# Gemini Resilience Report — Valorant AI Coach Assistant

| Field | Value |
| --- | --- |
| **Component** | `frontend/streamlit_app/utils/gemini_client.py` |
| **Test suite** | `frontend/streamlit_app/tests/test_gemini_resilience.py` |
| **Result** | 81 of 81 checks passed, exit status `0` |
| **Environment** | Python 3.12.13, Streamlit 1.60.0, executed from the repository root |
| **API calls consumed** | None |

## 1. Purpose

This report documents the hardening applied to the Gemini integration that powers
the **AI Coach** chatbot, and the evidence gathered to demonstrate that the
feature degrades gracefully rather than failing visibly. The motivating incident
was a runtime error surfaced verbatim in the user interface:

> 503 UNAVAILABLE. This model is currently experiencing high demand. Please try
> again later.

The relevant observation is that this was **not a programming defect**. The call
to Google was well formed and the credential was valid; the model was simply
saturated at that moment. The defect was in the *response to failure*: the client
queried a single model and, on the first refusal, relayed the provider's raw
diagnostic to the user. For an application intended to be demonstrated live in
front of an audience, a transient upstream condition was therefore
indistinguishable from a broken system.

The hardening addresses three separate concerns: recovering automatically where
recovery is possible, distinguishing failures that justify a retry from those
that do not, and ensuring that whatever remains unrecoverable is communicated in
language the audience can act upon.

## 2. Resilience strategy

### 2.1 An ordered chain instead of a single model

The client no longer depends on the availability of one model. It walks an
ordered chain, moving to the next entry only when the current one is exhausted.

| Order | Model | Role |
| --- | --- | --- |
| 1 | `GEMINI_MODEL`, or `gemini-2.5-flash` by default | Primary model |
| 2 | `gemini-2.5-flash-lite` | Lighter variant, usually less contended |
| 3 | `gemini-3.5-flash` | Newer generation, last resort |

Setting `GEMINI_MODEL` **replaces only the first position and preserves the
remaining fallbacks**. This detail matters more than it appears: the intuitive
implementation — treating the configured value as *the* model — would silently
reintroduce the single point of failure this work exists to remove, precisely for
the operator who took the trouble to configure something. The chain also
de-duplicates, so nominating a model that already belongs to it promotes that
entry rather than repeating it.

### 2.2 Bounded retries with incremental backoff

Each model is attempted up to three times, with waits of one and then two
seconds between attempts.

| Attempt | Wait before it | Rationale |
| --- | --- | --- |
| 1 | — | Most requests succeed here |
| 2 | 1 s | Absorbs a brief demand spike |
| 3 | 2 s | Gives a longer contention window time to clear |

The schedule is deliberately short. A live demonstration cannot tolerate a client
that spends thirty seconds before admitting defeat, so the budget favours a quick
traversal of the chain over exhaustive persistence on one model. In total, a
fully saturated chain resolves in roughly nine seconds of waiting rather than
failing instantly or hanging indefinitely.

The delay is injected as a `sleep` callable rather than calling
`time.sleep` directly. This is what allows the suite to assert the exact backoff
schedule without the tests actually waiting, and it keeps the production default
unchanged.

### 2.3 Classification by status code, not by message text

Failures are classified using the **numeric status code** that the SDK exposes on
`APIError.code`, not by searching the error message for keywords.

| Condition | Codes | Treatment |
| --- | --- | --- |
| Transient | `429`, `500`, `502`, `503`, `504` | Retry, then fall back |
| Authentication | `401`, `403` | Fail immediately, no retry |
| Model unavailable | `404` | Try the next model, no retry |
| Network | `TimeoutError`, `ConnectionError` | Retry, then fall back |

Two consequences of this choice are worth stating explicitly. First, the
behaviour is independent of language and of how Google chooses to word its
diagnostics in future releases — a text-matching classifier would quietly stop
recognising a `503` the day the wording changed. Second, a rejected credential
fails on the first attempt, because retrying an invalid key three times across
three models cannot succeed and merely delays the honest answer by nine seconds.

A network timeout receives particular attention. During development the suite
exposed a genuine defect here: a `TimeoutError` carrying the message
`connection timed out` was **not** classified as transient, because the detector
searched for the substring `timeout` while the message uses the participle *timed
out*. The fix was to classify by exception type rather than by wording, which is
the same principle already applied to status codes.

## 3. User-facing messages

Every technical detail is written to the server log; the interface shows only the
following closed set of messages, in Spanish and oriented towards what the user
can do next.

| Situation | Message |
| --- | --- |
| Whole chain saturated, rate limited, or timing out | El servicio de IA está temporalmente saturado. Inténtalo de nuevo en unos segundos. |
| Credential rejected, or no model reachable | La configuración del servicio de IA necesita revisión. |
| Unclassified fault | El coach tuvo un problema inesperado. Inténtalo de nuevo. |
| Credential absent | Configura GEMINI_API_KEY para activar el coach. |
| Model returned nothing | El coach no devolvió contenido. Reformula la pregunta e inténtalo de nuevo. |

The user interface adds a final barrier around the call to the coach: an
unqualified exception handler that logs the fault and displays the generic
message. It is not there to compensate for a known weakness — the client already
classifies every failure it can encounter. It exists so that an unforeseen bug in
future work cannot render a Python traceback in a publicly reachable deployment.

When a fallback model produces the answer, the page notes it in a small caption
beneath the reply. Suppressing that detail entirely would have been simpler, but
during an academic demonstration the resilience mechanism is itself part of what
is being presented, and a silent substitution would make it invisible.

## 4. Test methodology

The suite is designed around two constraints that make it safe to run
anywhere, including in continuous integration.

**The Gemini API is never contacted.** A test double reproduces the narrow
surface of `google.genai.Client` that the production code actually uses —
`chats.create` and `send_message` — so any failure mode can be provoked
deterministically. No quota is consumed and no credential is required, which also
means the suite cannot fail for reasons unrelated to the code under test.

**The environment is sanitised before import.** Any inherited `GEMINI_API_KEY` or
`GOOGLE_API_KEY` is removed from the process environment, because a leaked
credential would make the "missing key" scenario pass for the wrong reason.

The double raises a `FakeAPIError` that carries a `.code` attribute. That this
substitute works at all is itself a demonstration of the classification design:
because the production code reads the numeric code rather than the message, a
minimal stand-in with the right code is indistinguishable from the real
exception.

## 5. Scenarios covered and results

| # | Scenario | Expected behaviour | Result |
| --- | --- | --- | --- |
| 1 | `GEMINI_API_KEY` not configured | Setup notice, page remains renderable, no exception | Passed |
| 2 | Rejected API key (`401`, `403`) | Configuration message, single attempt, no retry | Passed |
| 3 | Saturated model (`503`) | Three retries, fallback engages, user receives an answer | Passed |
| 4 | Empty reply (`None`, `""`, whitespace) | Friendly fallback message, no `None` leaked | Passed |
| 5 | Network timeout | Classified as transient, retried, absorbed by the fallback | Passed |

Alongside the five required scenarios the suite verifies the configuration
constants, the chain-override semantics, rate limiting (`429`), an unreachable
chain (`404` on every model), an unclassified fault, the integrity of the coaching
persona, and the absence of the deprecated SDK.

### Detailed findings

**Scenario 1.** `get_api_key()` returns `None`, `is_configured()` reports the
chat as unavailable, and constructing a client raises `GeminiConfigurationError`
whose message matches the specification verbatim. Because that exception derives
from `GeminiClientError`, the page renders a warning rather than crashing the
Streamlit run, which is what keeps the remaining pages of the application
unaffected. Verified end to end by removing the secrets file and the environment
variables before starting the server: all eight routes answered `HTTP 200` and the
log contained no exception.

**Scenario 2.** Both `401` and `403` produce the configuration message after a
single attempt, with no backoff recorded and no status code present in the text.

**Scenario 3.** The primary model was attempted exactly three times, the recorded
backoff schedule was exactly `[1.0, 2.0]`, control then passed to
`gemini-2.5-flash-lite`, and **a valid answer was delivered to the user**. The
complementary cases were also confirmed: a single transient blip resolves on the
second attempt without leaving the configured model, and when every model is
saturated the message contains none of `503`, `UNAVAILABLE`, `high demand`,
`Traceback`, or `google`.

**Scenario 4.** All three degenerate replies produce the same friendly message.
An empty prompt is additionally rejected before the API is contacted, so no quota
is spent on a request that cannot yield anything useful.

**Scenario 5.** `TimeoutError` and `ConnectionError` are recognised as transient,
including a bare `TimeoutError` with no message at all. A chain-wide timeout
reports the transient message and leaks no socket detail.

## 6. Reproducing the verification

```bash
# Resilience suite — no credential and no network required
python frontend/streamlit_app/tests/test_gemini_resilience.py

# Dependency resolution and page imports
python frontend/streamlit_app/verify_deployment.py
```

The suite exits with status `0` when every check passes and `1` otherwise, which
makes it usable as a pre-deployment gate.

## 7. Scope

The work was confined to failure handling. The coaching persona
(`utils/coach_persona.py`), the FastAPI backend, the Docker configuration, and
the visual design of the existing pages were left untouched, so the resilience
behaviour can be reviewed in isolation from the rest of the application.

---

*Prepared by Manus AI.*
