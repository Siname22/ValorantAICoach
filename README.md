# Valorant AI Coach

![Valorant AI Coach](assets/banner.png)

AI-powered VALORANT player analytics and coaching, with FastAPI, real data
providers and a Streamlit frontend with a Gemini assistant.

## Development Status

Current branch: `codex/system-integration`.
Backend version: 0.4.0.

The integration is published in draft [PR #8](https://github.com/Siname22/ValorantAICoach/pull/8).
The authenticated GitHub connector preserved the exact local Git tree and
original history; local Git push still requires renewed authentication.
`main` is unchanged and merging requires the owner's approval.
Remote Python 3.12/3.13 and container checks passed for commit `2a3f937`.
CI reproduced the startup connection reset and recovered with bounded retries,
then verified liveness 200 and the no-provider 503. The real-curl regression
tests also passed on Linux with no skips. The PR shows checks for subsequent
updates. Passing CI is not a production-release claim.

The backend foundation was verified before the current integration: player
identity, rank/history fallback, Riot match detail, explicit provider failures,
and application-scoped HTTP client cleanup. The current branch also incorporates
the Streamlit/Gemini work from `develop`.

**Development integration, not a production release.** Backend and frontend
verification: 373 pytest tests passed, with one upstream Starlette deprecation
warning; the separate Gemini resilience script passed 81 checks. Ruff and
Black passed across 104 Python files, including the Alembic environment.
Live provider credentials and public
deployment have not been verified. See [roadmap](docs/ROADMAP.md) and
[delivery plan](docs/DELIVERY_PLAN.md) for the complete remaining scope.

## Local Setup

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required. From the repository root:

```powershell
uv sync --frozen --extra frontend
Copy-Item .env.example .env
uv run --frozen --extra frontend uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

For the frontend, use a second terminal:

```powershell
uv run --frozen --extra frontend streamlit run frontend/streamlit_app/app.py
```

Open [Streamlit](http://localhost:8501) or [API documentation](http://127.0.0.1:8000/docs).
Frontend dependencies are an optional extra; backend-only installs remain small.

The backend reads `.env`; Streamlit reads process environment or
`.streamlit/secrets.toml`, not the backend's dotenv file. Copy
`.streamlit/secrets.toml.example` for frontend settings.
Do not commit secrets or share API keys in issues, PRs or chat.

## Providers and Data Semantics

Set one or more backend keys: `HENRIK_API_KEY`,
`TRACKER_API_KEY`, `RIOT_API_KEY`.
A blank key or `<PROVIDER>_ENABLED=false` disables that provider.
Restart the backend after configuration changes.

- Henrik: account identity, current rank/RR and stored match summaries. Account
  region is resolved automatically, or history accepts `?region=eu`.
  Stored history may be incomplete.
- Tracker: profiles, lifetime stats, rank and recent matches, subject to API access.
- Riot: real account-v1 and VAL match API calls. The official API does not expose
  current player rank/RR. Key permissions and the selected shard matter.

The example targets Europe. `RIOT_REGION` derives the shard host only when
`RIOT_BASE_URL` is unset. If using the explicit URL in the example/Compose,
change that URL as well when selecting another shard. Continental account routing
uses the independent `RIOT_ACCOUNT_BASE_URL`.

Match summaries include provider provenance. Riot map/character IDs are not yet
resolved to display names. Timestamps retain provider formats. Henrik's raw
`stats.score` has no documented total/average meaning: the normalized
`score` is null and the original is retained in `provider_score`.
See the [stored-match contract](https://docs.henrikdev.xyz/valorant/guides/stored-matches.md)
and [OpenAPI schema](https://api.henrikdev.xyz/openapi.json).

## API

```text
GET /players/{game}/{tag}
GET /players/{game}/{tag}/rank
GET /players/{game}/{tag}/matches?region=eu&limit=5
GET /players/{game}/{tag}/stats
GET /players/{game}/{tag}/overview?limit=5
GET /matches/{matchId}
GET /health
GET /health/live
```

History limits are 1-20, default 10. Full match detail requires Riot.
`404` means all applicable providers confirmed absence; `503` means
unavailable/disabled capability; `502` means malformed upstream data.
A valid empty history returns 200 with an empty list. Invalid input returns 422.

Lifetime statistics require Tracker and reject invalid counters/non-finite
values rather than truncating or fabricating data. The overview preserves identity when
optional sections fail and distinguishes unavailable history from confirmed
empty history.

Streamlit opens on player lookup. Search results survive reruns without repeated
requests; rank/history outages preserve available data. Displayed provider text
is escaped and RR zero remains visible. Roadmap screens use explicit milestones,
not invented completion percentages.

## Persistence Status

PostgreSQL, SQLAlchemy and Alembic are declared dependencies, not working player
or match storage. No application tables or migration revisions exist yet;
Alembic's metadata is not connected to application models.

The preflight URL interpolation failure is fixed: percent-encoded credentials
now survive Alembic configuration without altering the URL supplied to
SQLAlchemy. Eight regressions cover plain URLs, encoded credentials, separators
and repeated percent signs in offline/online configuration. Online tests
intercept the connection before database access; offline SQL is generated,
not executed. This does not prove working storage or a production migration.
See the [version-matched configuration contract](https://github.com/sqlalchemy/alembic/blob/rel_1_18_5/alembic/config.py).

The proposed next step is PostgreSQL production storage with SQLite tests,
explicit activation and provider/timestamp provenance, pending design approval.

## Gemini Coach

The existing assistant uses the official `google-genai` SDK.
Configure `GEMINI_API_KEY` in Streamlit secrets or environment;
`GEMINI_MODEL` selects the preferred model. No key means the coach is disabled.
The current chat is general coaching: automatic live-player context, persistent
memory and grounded match reports remain separate delivery milestones.
SDK transport phases have 10-second timeouts. The wrapper controls retries
without multiplying the SDK's own attempts, handles actual HTTPX transport
failures, closes the client after each turn, and sanitizes logs and errors.
This is not a total wall-clock deadline. See the
[SDK documentation](https://github.com/googleapis/python-genai) and
[HTTPX exception hierarchy](https://www.python-httpx.org/exceptions/).

For frontend-only Streamlit Cloud installs, the entrypoint is
`frontend/streamlit_app/app.py` and its adjacent
`requirements.txt` supplies the frontend dependencies. Host FastAPI separately
and set `VALORANT_API_BASE_URL` to that backend.
See [chat setup](docs/chatbot_installation.md).

## Quality and Deployment

```powershell
uv run --frozen --extra frontend pytest -q tests frontend/streamlit_app/tests
uv run --frozen --extra frontend python frontend/streamlit_app/tests/test_gemini_resilience.py
uv run --frozen --extra frontend ruff check .
uv run --frozen --extra frontend black --workers 1 --check backend tests agents frontend database
docker compose up --build
```

GitHub CI is configured for locked Python 3.12/3.13 tests, page imports, Gemini
resilience, lint/format checks, and a production container build/liveness smoke test.
Its configuration follows the [official uv Actions guide](https://docs.astral.sh/uv/guides/integration/github/).
Provider tests simulate HTTP responses and do not prove real key access.
Docker build/runtime has not run locally. Remote CI at `2a3f937` verified the
image build, non-root execution, production imports, startup liveness and the
no-provider 503. Real upstream and hosted deployment smoke tests remain gates. The
liveness command retries startup transport failures while retaining HTTP
failure detection and bounded connect/request/retry waits; a final in-flight
attempt can outlast the retry budget. Local browser checks covered player
lookup and the missing-provider error at 375, 768 and 1280 pixel widths; real
player success and partial results are covered by simulated Streamlit AppTest.
Compose is development configuration with reload, exposed ports and local
database defaults, not a hardened public deployment. Authentication, quota limits
and production readiness must be completed before public access.

## Architecture and Roadmap

[Architecture](docs/Architecture.md) separates implemented components from plans.
The delivery plan retains persistence, measurable analysis, grounded AI reports,
dashboard/history, authentication/linking, background jobs, OCR/screenshots,
evidenced timeline/tactics, persistent agent memory and production deployment.
No milestone is complete solely because scaffolding or a percentage chart exists.

## License and Contributions

Source available for viewing, study and evaluation under the owner's
[proprietary license](LICENSE). This is not an open-source project.

Work on a dedicated branch, maintain this README when creating branches or
pushing changes, and submit a pull request against `main`.
The owner reviews and approves merges; do not commit directly to `main`.

[Repository](https://github.com/Siname22/ValorantAICoach)
