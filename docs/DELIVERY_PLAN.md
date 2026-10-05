# Delivery Plan: December 2026

## Scope and Technology Decision

Complete the full Valorant AI Coach product, not only its backend scaffolding.
Retain Streamlit/Gemini already present in develop; FastAPI owns the provider
integration, analysis and persistence boundaries. PostgreSQL is the production
database. Other UI/LLM platforms remain alternatives, not prerequisites.

Target dates are planning checkpoints, not delivery guarantees. Current
credentials, Docker availability and hosting must be established early.

## Milestones and Acceptance

| Target | Delivery | Required evidence |
| --- | --- | --- |
| October 12 | Integrated provider API and Streamlit player lookup; CI | Backend/frontend tests, partial-data and HTTP-failure cases, browser smoke test, passing PR checks |
| October 23 | SQLAlchemy player/match/report persistence, Alembic, refresh/cache policy, normalized dates/content IDs | Migration upgrade/downgrade, PostgreSQL integration, restart retention, provenance and refresh-limit tests |
| November 6 | Measurable match analysis and grounded personalized Gemini reports | Hand-calculated metric fixtures, source-linked report schema, actual player context, missing-data/LLM timeout and budget tests |
| November 13 | Player linking/authentication, dashboard/report history, background jobs and agent memory | Ownership/isolation tests, job retries and limits, session/memory persistence, end-to-end UI workflows |
| November 20 | OCR/screenshot intake and evidenced timeline/tactical analysis | Labeled screenshot fixtures, measured extraction accuracy, actual round-event evidence, uncertain claims surfaced rather than invented |
| November 30 | Release candidate and production configuration | CI, Docker build/run, real provider and Gemini smoke tests, readiness/auth/quota gates, hosted UI/backend checks |
| December 10 | Final delivery and documentation | Requirement-by-requirement audit, no unresolved release blockers, reproducible setup, owner-reviewed GitHub publication |

If a milestone slips, revise the date and dependencies explicitly. Do not silently
drop OCR, tactics, memory, authentication or persistence, or claim that a scaffold
implements them. Advanced reports must identify the actual evidence supporting
their conclusions; a generic chatbot is not a personalized match analyst.

## Current Integration

- Branch: codex/system-integration; local integration verified, GitHub publication
  is being prepared as a pull request against main for owner approval.
- Backend foundation commit: 354dcaf; pre-integration verification: 282 tests
  passed with one Starlette deprecation warning; Ruff and Black passed.
- Codex Security diff scan b4fffd08-3b8d-4554-bfdb-6a9c343bd9cd completed with
  no reportable findings for the frozen backend patch. Later integration edits
  are not covered by that result.
- develop's Streamlit/Gemini files are incorporated in integration commit
  41b6d6e. main's owner license/contribution policy is preserved; its README
  conflict is resolved with current setup, evidence and full planned scope.
- Lifetime-stat and aggregated-profile routes are being recovered without
  breaking the existing flat profile API. Regression tests now cover valid and
  invalid statistics, optional-section failures, empty history and identity 404.
- Frontend HTTP/partial-data fixes and tests are integrated. The app opens on
  search, uses configured API documentation links and explicit roadmap states.
  Gemini logs no longer expose raw upstream exception bodies.
- Integrated local verification: 362 pytest tests passed with one upstream
  Starlette warning; 81 standalone Gemini checks passed; Ruff and Black passed
  across 101 Python files. Production-only backend imports passed without
  pytest/Streamlit. Browser checks at 375/768/1280px verified bounded form layout
  and the actual missing-provider error; no live credential access is implied.
  CI configuration is present, but remote jobs/publication remain pending.
- The usage limit reset and the normal approval workflow resumed successfully.
  No approval check was bypassed. Independent review found malformed history,
  impossible metric values, private final-handler logs, missing SDK transport
  timeout and real HTTPX errors not retried. Tests reproduced these before
  correction; focused independent re-review closed all five findings and
  verified client cleanup on success/failure. Production certification remains
  outside that review's scope.

## Publication Gate

1. Finish conflict resolutions and check the merged service contracts.
2. Run backend and frontend tests, Gemini resilience script, Ruff, Black and
   diff checks. Verify a production-only dependency environment independently.
3. Confirm interface behavior and the exact current commit in an independent
   review; rerun after relevant fixes.
4. Integrate main's owner license changes and ancestry without overwriting
   either side's work. The current LICENSE mirrors origin/main's owner text.
5. Update README with actual branch/status/test evidence, push the feature
   branch, create/attach a pull request against main, inspect CI and review.
6. Never merge into main autonomously or present a PR as a deployed release.

## Access Needed

GitHub access already works. No matching Valorant app was found in Base44;
no Base44 migration or remote build was initiated. GH Review Loop requires an
authenticated gh CLI and selected reviewer; Agent Parley requires its missing
CLI/session setup. Neither workflow has been reported as completed.

Real-provider validation requires keys configured privately in .env (at least
one accessible player-data provider) and a test Riot ID/region. Gemini needs a
private frontend secret. Hosting and Docker are needed for the production gate.
Never put keys into README, PR descriptions, issues or conversation messages.
