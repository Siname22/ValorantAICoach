# Storage and Robustness Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the approved persistence foundation and bounded frontend/provider behavior without changing existing REST responses.

**Architecture:** Keep FastAPI, Streamlit and Gemini. Store successful provider-backed reads with provenance and UTC observation times using SQLAlchemy/Alembic; PostgreSQL is production storage and SQLite is isolated test storage. Database activation and migration execution are explicit, and no live credentials or existing database are used by tests.

**Tech Stack:** Locked SQLAlchemy 2.0.51, Alembic 1.18.5, psycopg 3.3.4, Streamlit 1.65.0, pytest/respx/AppTest.

## Global Constraints

- The owner approved these robustness changes and PostgreSQL/SQLite architecture on October 6, 2026.
- Preserve existing API schemas, partial-data/error semantics, owner license and unrelated work.
- No automatic migration/table creation at application startup, deployment or merge to main.
- Source-backed reports, authentication/linking, jobs, OCR/tactics and durable agent memory remain in the full delivery plan; this update does not declare those milestones complete.
- Record behavioral RED before production edits, focused GREEN, integration tests and independent review. Update README before publication and verify the exact PR revision.

---

### Task 1: Bounded Frontend and Provider Operations

**Files:** Modify `frontend/streamlit_app/components/sections.py`, `frontend/streamlit_app/utils/gemini_client.py`, `backend/providers/riot/client.py`, `.devcontainer/devcontainer.json`; create focused frontend/provider/devcontainer tests and small frontend policy helper if needed.

**Interfaces:** Existing `GeminiCoachClient` chat, Streamlit session state/avatar rendering and Riot HTTP retry loop remain public entry points. Enforce 4000 input characters, 20 completed exchanges/128 KiB retained content, valid HTTPS avatars and a 30-second Riot header delay cap. Restore framework origin protections.

- [x] Add tests for oversized prompts, pair-preserving retention, invalid avatar paths and real intercepted retry delays; execute the devcontainer command with intercepted `streamlit` to inspect effective protections.
- [x] Observe the expected focused failures without network, real keys or long sleeps.
- [x] Implement only the specified bounds, preserving failure cleanup and valid profiles.
- [x] Run focused and existing frontend/provider tests plus Ruff/Black.
- [x] Independent review and aggregate commit after integration checks.

### Task 2: Explicit Schema and Migrations

**Files:** Create `backend/app/storage/models.py`, `backend/app/storage/__init__.py`, `database/migrations/versions/20261006_01_initial_storage.py`, `tests/test_persistence.py`; modify `database/migrations/env.py`.

**Interfaces:** `Base.metadata` owns player, provider snapshot, match/history and future report records. `alembic upgrade head` creates them and `alembic downgrade base` removes them in reverse FK order. Observation times are UTC; original provider timestamps and payloads are retained.

- [x] Run a real SQLite Alembic command and assert the expected tables exist; existing empty revisions must fail this assertion.
- [x] Implement mapped models, explicit revision and metadata wiring without `create_all` in startup.
- [x] Verify upgrade/repeated upgrade/downgrade/re-upgrade and metadata parity on a temporary database.
- [x] Retain the existing encoded-URL tests; compile PostgreSQL offline SQL with no connection.
- [x] Independent review and aggregate commit after integration checks.

### Task 3: Activated Storage, Refresh and Restart Retention

**Files:** Create `backend/app/storage/repository.py`, `backend/app/storage/player_service.py`, focused persistence integration tests and a separately invoked PostgreSQL CI test. Modify backend settings, provider factory/service, `.env.example`, Compose, CI and README/delivery documentation.

**Interfaces:** `DATABASE_ENABLED=false` keeps current provider-only behavior. With activation, a migrated store caches successful profile/rank/stat/history/detail reads for configured TTL, keeps limit/region/identity keys separate, and uses provider provenance for confirmed-empty history. Synchronous DB work runs outside the async request event loop. Errors and 404/503 responses are never cached; expired data is not represented as fresh. Missing schema/storage failure is sanitized and does not create tables automatically.

- [x] Assert a real REST profile survives application restart with one intercepted provider call, then observe the provider-only implementation fail the call-count assertion.
- [x] Implement typed cache revalidation, transactional records and thread-safe connection lifecycle; verify TTL expiry, empty history, lookup isolation, corrupt cache, DB failure and provider failure semantics.
- [x] Add a PostgreSQL service CI job that actually upgrades, tests restart retention/schema integrity and downgrades; no silent skip when that job runs.
- [x] Run full backend/frontend pytest, Gemini resilience, imports, Ruff, Black and whitespace checks; independently review changed paths.
- [x] Update README with actual evidence, publish the integration branch and inspect exact-head CI. Do not merge or deploy.

## Evidence and Limits

Baseline before implementation: 373 pytest tests passed, one Starlette warning, no skips (October 6). The sealed security integration scan covers the old head `9654beff`, with four deferred proof gaps and no confirmed reportable finding. Later robustness changes require their own evidence; they are not a completed exploitation/remediation certification.

[SQLAlchemy 2.0 declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html) and [SQLite foreign-key behavior](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support) informed the implementation boundaries. The Alembic URL regression remains version-matched to the existing lock.

No unresolved architecture choice blocks this approved wave. Live provider keys, production hosting and the ownership policy for future reports remain external release gates, not implied completed features.

## October 6 Verification

- Full command: `.venv/Scripts/python.exe -B -m pytest -q tests frontend/streamlit_app/tests --basetemp <owned-OS-temp-directory> -p no:cacheprovider`: 493 passed, no skips, 25 dependency warnings. Gemini script: 81/81; page imports: passed. Ruff: passed; Black: 115 unchanged files; whitespace: passed.
- Additional PostgreSQL target guards: 16 passed/3 deselected, without connections. Offline Alembic PostgreSQL DDL generation succeeded for all five tables and UTC columns; it is not execution against PostgreSQL.
- Behavioral RED/GREEN covered schema creation, API restart retention, section caching, invalid detail/partial schema, nonblocking startup, deterministic shared-row writes, chat bounds, avatars, devcontainer protections and retry limits. Supplementary risk tests characterize existing behavior, not invented RED claims.
- Full-suite RED exposed migration logging interference (4 failed/482 passed); focused RED 4 failed/23 passed became GREEN 27 passed with existing loggers preserved, followed by the full suite above.
- Independent reviews closed the three P2 issues (startup thread, shared-row ordering, hexadecimal avatar hosts) after focused re-tests. Scoped branch publication was approved; no main merge or production release was approved.
- PostgreSQL real execution passed in CI run 37436302896 for source head `16146ab`: 19 tests, no skips. Python 3.12/3.13 and container jobs passed. Simultaneous PostgreSQL transactions, live providers and deployment remain unverified. Cache retention cleanup/configuration invalidation and distributed quotas remain open.
- Native Git dry-run push still rejected its credential on October 6. Publication uses the already authenticated GitHub connector, non-forced branch updates and exact-tree verification; no authentication gate is bypassed.
- Runtime commit: local `aff61ee` / remote `16146ab`, tree `00e10e8ce4190a46bfc84f45ce572dd2e7fa2a32`. History-only local merge `c8774a6` retained both ancestries with zero source delta. A documentation-only follow-up records CI proof and must receive its own checks.
