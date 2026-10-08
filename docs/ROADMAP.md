# Roadmap

## Completed: 0.4.0 Provider Integration

- [x] Start the backend without external credentials.
- [x] Allow independent configuration and disabling of providers.
- [x] Report disabled or misconfigured providers and separate liveness from API health.
- [x] Use real Riot account and match endpoints with correct authentication/routing.
- [x] Retrieve current rank/RR from Henrik, without fabricated Riot rank data.
- [x] Parse stored Henrik match summaries and use the player's actual region.
- [x] Distinguish confirmed absence, empty history and provider outages.
- [x] Limit match history requests and expose full Riot match details by ID.
- [x] Close provider HTTP connections at application shutdown.
- [x] Include HTTP dependencies and provider configuration in deployment.
- [x] Cover provider HTTP contracts and application failure paths with automated tests.

Live external API access still needs provider credentials and appropriate
permissions. Mocked HTTP tests do not confirm those permissions.

## Completed: Stored Player Intelligence & Persistence

- [x] Add SQLAlchemy player, match and future-report models and explicit Alembic migration.
- [x] Add opt-in typed TTL caching with UTC observations and provider provenance.
- [x] Verify the PostgreSQL service job for published source (19 persistence tests).
- [x] Add retention cleanup (`SQLPlayerStore.prune_expired_snapshots`, `POST /system/cache/prune`, `DELETE /players/{game}/{tag}/cache`).
- [x] Add automated periodic background cache pruning worker in FastAPI lifespan.
- [x] Resolve Riot map/character IDs using a versioned content catalog.
- [x] Normalize stored match dates to UTC while preserving raw provider values.
- [x] Implement measurable match analysis and useful report schemas.
- [x] Connect the match analyst, specialized coaching agents (tactical, economy, aim, agent), and orchestrator to the player service.

## Completed: Usable Application & Decoupled Frontend

- [x] Build the player dashboard, match history, and coaching report views (Streamlit UI).
- [x] Interactive Multi-Agent coaching report generation cards and historical reports browser.
- [x] Add coaching report persistence (`coaching_reports` table) and REST endpoints.
- [x] Add a provider-aware readiness endpoint (`GET /health/ready`) and storage health check.
- [x] Isolate frontend and backend runtimes, containers, dependencies, and test suites.
- [x] Add containerized Docker Compose orchestration with isolated virtual environments.
- [x] Integrate a configured LLM with automatic 3-model failover, exponential backoff, and 81/81 resilience tests.

## Completed: User Authentication & Linked Player Accounts

- [x] Add `users` and `linked_player_accounts` relational tables with Alembic migration.
- [x] Implement secure PBKDF2-HMAC-SHA256 password hashing with salt and constant-time verification.
- [x] Implement cryptographically signed HS256 JWT access tokens with expiration.
- [x] Add `/auth/register`, `/auth/login`, and `/auth/me` endpoints.
- [x] Add `/auth/me/accounts` for linking, listing, and unlinking Riot player identities.
- [x] Ensure per-user account isolation and primary identity management.
- [x] Update Streamlit `APIClient` with bearer token authentication and auth methods.

## Completed: Player Progression Trajectory & Scheduled Coaching Jobs

- [x] Add `last_synced_at` column to `linked_player_accounts` with Alembic migration.
- [x] Implement player trajectory analytics (`GET /players/{game}/{tag}/progression`) evaluating rolling K/D, win rate, headshot rates, agent mastery, and trend classification (improving, declining, stable).
- [x] Implement dynamic weakness resolution tracking (detects resolved vs active focus areas across consecutive coaching reports).
- [x] Implement on-demand match and coaching synchronization (`POST /players/{game}/{tag}/sync`).
- [x] Implement tracked accounts batch synchronization (`POST /system/coaching/sync-tracked`).
- [x] Add automated background coaching sync worker in FastAPI `lifespan` governed by `database_auto_sync_interval_seconds`.
- [x] Expose progression metrics, visual trajectory delta indicators, and on-demand synchronization in Streamlit frontend.

## Completed: Computer Vision & Scoreboard OCR Ingestion

- [x] Implement `ScoreboardVisionService` supporting multimodal image understanding (Google Gemini `gemini-2.5-flash`) with resilient heuristic OCR fallback.
- [x] Validate and decode image payloads (PNG, JPEG, WebP) with magic byte detection and size safety guards.
- [x] Structured scoreboard extraction: map resolution, game mode, match outcome, rounds won/lost, and per-player telemetry (ACS, K/D/A, ADR, first bloods).
- [x] Direct persistence integration: convert extracted scoreboard into domain `PlayerMatch` and persist into PostgreSQL / SQLite history.
- [x] Expose vision endpoints: `POST /vision/scoreboard/analyze` (base64/data URL), `POST /vision/scoreboard/upload` (multipart file), and `POST /players/{game}/{tag}/scoreboard`.
- [x] Add interactive Streamlit UI section with image preview, confidence scores, extracted player tables, and tactical takeaways.

## Next Milestones

- [ ] Add round-by-round replay timeline analysis.
- [ ] Implement team synergy & counter-pick recommendation engine.
- [ ] Production deployment hardening, security audit, and Release 1.0.


