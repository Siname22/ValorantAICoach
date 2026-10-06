# Valorant AI Coach

## Vision

Create an AI-powered coaching platform capable of collecting, analyzing and explaining Valorant team performance.

---

## Tech Stack

Backend
- FastAPI

Frontend
- Streamlit: existing UI, retained for the December delivery.

Database
- PostgreSQL

AI
- Google Gemini via google-genai: existing general coaching chat.
- Grounded match reports and persistent memory: pending.
- Ollama/PydanticAI: possible future integrations, not current runtime.

Scraping
- Playwright

OCR
- PaddleOCR

Deployment
- Docker

## Implementation Boundaries

Player data flows from Streamlit over HTTP to FastAPI, PlayerService and the
configured Tracker/Henrik/Riot providers. The backend owns provider keys and
lifespan-scoped clients. The frontend never requires backend provider keys.

PostgreSQL/SQLAlchemy/Alembic now provide opt-in player snapshots and match/history
storage with an explicit migration. SQLite is isolated test storage only. The
cache revalidates typed data, expires reads, retains provider/UTC provenance and
runs blocking database work outside the async event loop. Startup does not run
migrations. The report table is schema only; reports are not generated yet.
OCR, computer vision,
tactical timelines, authentication, background jobs and agent memory remain
planned modules, not working features. The Gemini chat does not automatically
consume live player data yet.

Angular is not part of the selected delivery architecture. Migrating the UI
would duplicate existing work without advancing the immediate player/report
workflow. This decision preserves the complete product scope, not just a demo.

See DELIVERY_PLAN.md for acceptance gates and dates.

---

## Modules

Backend

Frontend

Scraper

Database

Agents

Analytics

Authentication

Reports

Dashboard
