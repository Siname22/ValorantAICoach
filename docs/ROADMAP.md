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

## Next Milestones

- [ ] Add user authentication, sessions, and player account linking.
- [ ] Add scheduled coaching update jobs for tracked players.
- [ ] Implement OCR / screenshot ingestion and computer vision for scoreboard analysis.
- [ ] Add round-by-round replay timeline analysis.
- [ ] Connect long-term persistent agent memory to player trajectory over time.
