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

## Next: Stored Player Intelligence

- [ ] Add SQLAlchemy player, match and report models and Alembic migrations.
- [ ] Cache provider data with timestamps, provenance and refresh limits.
- [ ] Resolve Riot map/character IDs using a versioned content catalog.
- [ ] Normalize timestamps to one documented representation.
- [ ] Implement measurable match analysis and useful report schemas.
- [ ] Connect the match analyst and orchestrator to the player service.

## Next: Usable Application

- [ ] Build the player dashboard, match history and report views.
- [ ] Add authentication and player account linking.
- [ ] Add report persistence and background jobs.
- [ ] Add a provider-aware readiness endpoint when deployment depends on data access.

## Later: AI and Visual Analysis

- [ ] Integrate a configured LLM with timeouts, cost limits and failure handling.
- [ ] Implement OCR/screenshot ingestion and computer vision.
- [ ] Add timeline and tactical analysis with evidence from the match.
- [ ] Connect persistent agent memory to player history.
