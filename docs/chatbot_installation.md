# AI Coach Chatbot — Installation Guide

| Field | Value |
| --- | --- |
| **Student name** | Raúl Poblete Illescas |
| **Delivery date** | Pending |
| **Page link** | Pending deployment |
| **Platform** | Streamlit + Google Gemini |

This guide explains how to enable the **Valorant AI Coach Assistant**, the
conversational coaching feature of the Streamlit frontend, powered by Google AI
Studio (Gemini).

## Installation at a glance

1. Create an API key in Google AI Studio.
2. Add the `GEMINI_API_KEY` secret.
3. Install the dependencies.
4. Run Streamlit.
5. Open the chatbot from the **AI Coach** entry in the sidebar.

Each step is detailed in the sections below.

The chatbot is an additive feature. If no API key is configured, the assistant
page displays a setup notice and every other page of the application continues
to work exactly as before.

---

## 1. Create a project in Google AI Studio

Google AI Studio is the web console used to obtain credentials for the Gemini
API. A personal Google account is enough; no billing setup is required for the
free tier.

1. Open [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Accept the terms of service if prompted.

> Google AI Studio and the Gemini API share the same credential. The key you
> create in the console is the key the application uses.

---

## 2. Obtain the API key

1. Navigate to [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Select **Create API key**.
3. Choose an existing Google Cloud project, or let the console create one for
   you.
4. Copy the generated key.

The key is a long alphanumeric string beginning with `AIza`. Treat it as a
password: it must never be committed to the repository, pasted into source
files, or shared in screenshots.

---

## 3. Configure Streamlit Secrets

The application reads its configuration from `st.secrets`, falling back to
environment variables. The key is never hardcoded.

### Local development

Copy the tracked template and fill in your own value:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
VALORANT_API_BASE_URL = "http://127.0.0.1:8000"
GEMINI_API_KEY = "your_key_here"
GEMINI_MODEL = "gemini-2.5-flash"
```

`.streamlit/secrets.toml` is listed in `.gitignore`, so it is never committed.
Only the `.example` template is versioned.

### Streamlit Community Cloud

Open the app dashboard, then **Settings → Secrets**, and paste the same content.
Saving the secrets restarts the application automatically.

### Configuration reference

| Key | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | — | Google AI Studio credential for the Gemini API |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | First Gemini model tried by the assistant |
| `VALORANT_API_BASE_URL` | No | `http://127.0.0.1:8000` | FastAPI backend consumed by the other pages |

The earlier name `GOOGLE_API_KEY` is still read as a fallback so that any
environment already configured with it keeps working, but `GEMINI_API_KEY` is the
supported name and the one that should be used.

### Model selection and automatic fallback

The Gemini API can reject a request with a temporary *high demand* response when
the requested model is saturated. Because a live demonstration cannot depend on
the availability of a single model, the client does not query one model and give
up. It walks an ordered chain instead:

| Order | Model | Role |
| --- | --- | --- |
| 1 | `GEMINI_MODEL`, or `gemini-2.5-flash` by default | Primary model |
| 2 | `gemini-2.5-flash-lite` | Lighter variant, usually less contended |
| 3 | `gemini-3.5-flash` | Newer generation, used as a last resort |

Each model is attempted up to three times with an incremental wait of one and
then two seconds. If the model remains unavailable, the client moves to the next
entry in the chain transparently. Only when every model has been exhausted does
the user see a message, and that message never exposes status codes or provider
details.

Setting `GEMINI_MODEL` overrides the first position without removing the
remaining fallbacks, so the model can be changed from the Community Cloud secrets
panel with no code change. When the answer is produced by a fallback rather than
the configured model, the page notes it discreetly beneath the reply.

---

## 4. Install dependencies and run the application

The frontend declares its dependencies in `frontend/streamlit_app/requirements.txt`,
which is the authoritative file for deployment. The chatbot adds a single
package, `google-genai`.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r frontend/streamlit_app/requirements.txt
streamlit run frontend/streamlit_app/app.py
```

The application becomes available at `http://localhost:8501`. Select **AI Coach**
in the sidebar to open the assistant.

Before starting the server you may run the bundled verification script, which
checks that the dependency file resolves as expected and that every page
imports cleanly:

```bash
python frontend/streamlit_app/verify_deployment.py
```

### Using the chatbot

The assistant opens with a welcome turn and four suggested questions that can be
used as a starting point. Questions may also be typed directly into the chat
input at the bottom of the page. The conversation history is preserved for the
duration of the browser session and can be cleared at any time with the **Reset
chat** button.

The coach is tuned for the Silver to Platinum ranks and answers in the language
you write in. The more context you provide — rank, role, map, and what went
wrong in the round — the more specific the advice will be.

---

## 5. Deploy

The chatbot requires no changes to the existing deployment configuration beyond
adding the new secret.

| Setting | Value |
| --- | --- |
| Repository | `Siname22/ValorantAICoach` |
| Branch | The branch connected in Community Cloud (currently `feature/player-service` holds these changes) |
| Main file path | `frontend/streamlit_app/app.py` |
| Python version | `3.12` |
| Dependencies | `frontend/streamlit_app/requirements.txt` |

Deployment steps:

1. Commit and push the changes to the branch connected in Community Cloud.
2. In Streamlit Community Cloud, add `GEMINI_API_KEY` under **Settings →
   Secrets**.
3. Wait for the automatic rebuild to finish, then open the **AI Coach** page.

> **Dependency resolution.** Community Cloud installs only the *first*
> dependency file it finds, searching the entrypoint directory before the
> repository root, with the priority `uv.lock` > `Pipfile` > `environment.yml` >
> `requirements.txt` > `pyproject.toml`. Because this repository tracks a
> `uv.lock` at the root for backend development, the frontend dependency file
> must remain next to `app.py` in order to take precedence. Do not move or
> delete it.

---

## Troubleshooting

| Symptom | Cause and resolution |
| --- | --- |
| *"Configura GEMINI_API_KEY para activar el coach."* | `GEMINI_API_KEY` is missing or empty. Add it to the secrets and reload the page. |
| *"El servicio de IA está temporalmente saturado. Inténtalo de nuevo en unos segundos."* | Every model in the chain reported saturation, a rate limit, or a network timeout. The retries and fallbacks already ran automatically, so simply retry after a few seconds. |
| *"La configuración del servicio de IA necesita revisión."* | The key was rejected (invalid or revoked), or no model in the chain is reachable with it. Generate a new key in Google AI Studio, or set `GEMINI_MODEL` to a model the key can access. |
| *"El coach tuvo un problema inesperado. Inténtalo de nuevo."* | An unclassified fault occurred. The technical detail is in the server log; the interface deliberately withholds it. |
| *"El coach no devolvió contenido. Reformula la pregunta e inténtalo de nuevo."* | The answer was blocked by a safety filter or hit the token limit. Rephrase the question. |
| A caption reports that a fallback model answered | Expected behaviour, not a fault: the configured model was unavailable and the chain absorbed it. |
| `ModuleNotFoundError: google` | `google-genai` was not installed. Confirm the dependency file resolved by Community Cloud is the one next to `app.py`. |

The resilience of this behaviour is covered by an automated suite that never
contacts the Gemini API, so it can be run at any time without consuming quota or
requiring a credential:

```bash
python frontend/streamlit_app/tests/test_gemini_resilience.py
```

The script exits with status `0` when every check passes, which makes it usable
as a pre-deployment gate. `docs/gemini_resilience_report.md` documents the
strategy and the recorded results.

---

## Security notes

The API key is read exclusively from `st.secrets` or the process environment and
is never written to source files, logs, or the user interface. The repository
tracks only `.streamlit/secrets.toml.example`, which contains placeholders. If a
key is ever exposed, revoke it in Google AI Studio and issue a replacement.

The Gemini credential is a frontend-facing secret and is deliberately kept
separate from backend provider keys such as `RIOT_API_KEY` and `TRACKER_API_KEY`,
which remain in the backend environment and are never exposed to Streamlit.
