# AI Coach chat in Angular

The `/coach` page is available to signed-in users of the Angular application.
It sends each question to `POST /v1/coach/chat` in FastAPI. The backend calls
Gemini; the browser never receives or stores the Gemini API key.

## Configuration

Set `GEMINI_API_KEY` in the **backend environment** before starting FastAPI or
Compose. `GEMINI_MODEL` optionally selects the first model to try; the default
is `gemini-3.1-flash-lite`. Do not put either value in Angular environment files or
commit a local `.env` file. Compose already forwards both variables to the
backend container. PostgreSQL and an authenticated account are required for
the normal sign-in flow; apply Alembic migrations before enabling persistence.

The backend tries the configured model, then the remaining fallback models.
Temporary provider errors are retried with backoff. A missing or rejected key,
an exhausted model chain, and an empty response produce a safe error in the
interface; the user may retry the question. Provider exception text is never
returned to the browser.

## Use and privacy

Select a player and region in Resumen, then open **AI Coach** from the sidebar.
The page also supports general questions without a selected player. When a
player is selected, FastAPI retrieves that player's profile and recent matches
for the selected region and verifies the profile region before sending a short
summary to Gemini. The client cannot provide its own statistics. The endpoint
requires a bearer token and does not use another user's saved reports.

The page offers four starter questions, a 4000-character input limit, and a
**Reiniciar chat** action. It retains at most 20 completed exchanges (40
messages, up to 128 KiB of UTF-8 history). The conversation lives only in the
current Angular session; changing the selected player or signing out clears it
and ignores responses to requests started in the previous session. Signing out
also clears the selected player from tab storage.

## Local validation on 28 November 2026

The authenticated Angular UI received four successful Gemini responses across
two player selections in the same verified region. A follow-up kept the prior
exchange; switching player, restarting the chat and signing out each cleared
the visible history. Requests without a session were rejected, and input and
history limits were checked separately. No personal response text was saved.

The former default model returned 404 for the locally authorized key. The
currently configured default succeeded in a direct SDK check and in the UI.
The UI does not expose token usage or billing data, so the monetary cost of
these requests could not be measured locally. Model availability can change;
`GEMINI_MODEL` remains configurable in the backend environment.

The Compose smoke check also confirmed that Nginx revalidates the SPA HTML on
both `/` and deep routes while retaining its security headers. This prevents
an older cached entry point from loading a stale Angular bundle after an update.

## Verification

From the repository root:

```text
uv run --no-sync pytest -q tests/test_chat.py
uv run --no-sync pytest -q
```

From `frontend/web`:

```text
node node_modules/@angular/cli/bin/ng.js build
node node_modules/eslint/bin/eslint.js src
node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless
```

For a live Gemini check, configure the key only in the backend environment,
start PostgreSQL and both application services, sign in, select a player with
provider data, and send a starter question. Confirm a response, retry behavior,
reset, and clearing after a player change or sign-out. A local check without a
Gemini key can verify the safe unavailable state but cannot prove live model
responses.
