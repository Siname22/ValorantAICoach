# Valorant AI Coach

![Valorant AI Coach](assets/banner.png)

> Professional AI-powered coaching and intelligence platform for VALORANT players built with Clean Architecture, FastAPI, PostgreSQL, Multi-Agent analysis, and resilient Google Gemini integration.

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-FF4B4B)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-565%20Passing-success)](https://pytest.org/)
[![Resilience](https://img.shields.io/badge/Gemini%20Resilience-81%2F81%20Verified-brightgreen)](https://ai.google.dev/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-red)](https://github.com/astral-sh/ruff)

---

## 🚀 Overview

**Valorant AI Coach** is an advanced analytics and intelligent coaching platform designed to elevate VALORANT player performance. Rather than acting as a static statistics viewer, the platform combines robust backend engineering, multi-provider data aggregation, persistent domain models, multi-agent tactical analysis, and a resilient generative AI coaching assistant.

### Key Pillars
- **Unified Multi-Provider Aggregation**: Transparent fallback across Tracker.gg, HenrikDev, and Riot Games APIs with automatic circuit breaking and error isolation.
- **Enterprise Persistence**: Production PostgreSQL 16 database managed via Alembic migrations, supporting atomic snapshot caching, player histories, coaching reports, and user identities.
- **User Authentication & Linked Accounts**: Secure PBKDF2-HMAC-SHA256 password hashing, cryptographically signed HS256 JWT access tokens, and multi-identity Riot player account linking with primary profile selection.
- **Backend & Frontend Isolation**: Headless FastAPI service and interactive Streamlit UI run in fully decoupled containers with independent dependencies and virtual environments.
- **Grounded Multi-Agent Coaching**: Specialized agents evaluate player telemetry (Aim, Economy, Positioning, Agent Utility) and compile structured, evidence-backed recommendations.
- **Resilient AI Coach**: Integrated Google Gemini assistant powered by the official SDK with an automatic 3-model fallback chain (`gemini-2.5-flash` &rarr; `gemini-2.5-flash-lite` &rarr; `gemini-3.5-flash`), exponential backoff, and 81/81 resilience validations.

---

## 🏗️ Architecture & Component Isolation

The platform enforces strict separation of concerns across service boundaries:

```text
                        ┌─────────────────────────────────────────┐
                        │      Streamlit Frontend (Port 8501)     │
                        │   (Isolated Container & Dependencies)   │
                        └────────────────────┬────────────────────┘
                                             │ HTTP REST
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │        FastAPI Backend (Port 8000)      │
                        │    (Clean Architecture / Service Layer)  │
                        └─────────┬───────────────────┬───────────┘
                                  │                   │
                 ┌────────────────┴──────────┐        │ Multi-Agent
                 ▼                           ▼        ▼
       ┌──────────────────┐       ┌──────────────────────┐
       │   SQLPlayerStore │       │  Multi-Agent System  │
       │  (PostgreSQL 16) │       │ (Tactical/Aim/Econ)  │
       └──────────────────┘       └──────────────────────┘
                 │
       ┌─────────┴─────────┬──────────────────┐
       ▼                   ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Tracker.gg  │   │  HenrikDev   │   │  Riot Games  │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Architectural Guarantees
1. **Frontend Isolation**: The frontend communicates with the backend solely over HTTP via `APIClient`. It maintains zero direct database or internal service bindings.
2. **Container Separation**: `docker/backend.Dockerfile` and `docker/frontend.Dockerfile` build isolated images with separate virtual environments (`backend_venv`, `frontend_venv`), eliminating dependency pollution.
3. **Test Isolation**: Backend unit tests do not require Streamlit or GUI libraries. Frontend test suites run independently, and optional dependencies use guard checks (`pytest.importorskip`).
4. **Data Privacy & Sanitization**: Error handlers and health probes strictly sanitize outputs. Sensitive keys and raw upstream payloads are never logged or leaked.

---

## 📊 REST API Reference

The FastAPI backend exposes comprehensive endpoints documented via OpenAPI/Swagger at `/docs`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Application metadata and status. |
| `GET` | `/health` | Aggregated health check of providers and core services. |
| `GET` | `/health/live` | Process liveness probe without querying external APIs. |
| `GET` | `/health/ready` | Readiness probe validating database connection and provider configs. |
| `POST` | `/system/cache/prune` | Admin endpoint to prune expired snapshot cache records. |
| `POST` | `/system/coaching/sync-tracked` | Batch coaching update for all primary tracked player accounts. |
| `POST` | `/auth/register` | Register a new user account with secure password hashing. |
| `POST` | `/auth/login` | Authenticate with credentials and receive a JWT bearer token. |
| `GET` | `/auth/me` | Retrieve profile information for the authenticated user. |
| `POST` | `/auth/me/accounts` | Link a Valorant player identity to the authenticated user. |
| `GET` | `/auth/me/accounts` | List all Riot player identities linked to the authenticated user. |
| `DELETE` | `/auth/me/accounts/{id}` | Unlink a player identity from the authenticated user. |
| `GET` | `/players/{game_name}/{tag_line}` | Unified player profile (level, card, rank, region). |
| `GET` | `/players/{game_name}/{tag_line}/rank` | Competitive rank tier, rank rating (RR), and MMR data. |
| `GET` | `/players/{game_name}/{tag_line}/matches` | Recent match history with normalized stats. |
| `GET` | `/players/{game_name}/{tag_line}/progression` | Long-term trajectory analytics (K/D, win rate, weakness resolution). |
| `GET` | `/players/{game_name}/{tag_line}/timeline-analytics` | Aggregated tactical timeline analytics (Attack vs Defense WR, trade efficiency, clutches). |
| `POST` | `/players/{game_name}/{tag_line}/sync` | On-demand match history synchronization and coaching update. |
| `POST` | `/vision/scoreboard/analyze` | Computer vision / OCR analysis of scoreboard screenshot (base64). |
| `POST` | `/vision/scoreboard/upload` | Direct multipart image file upload for scoreboard analysis. |
| `POST` | `/players/{game_name}/{tag_line}/scoreboard` | Analyze and ingest scoreboard screenshot for a specific player. |
| `GET` | `/matches/{match_id}` | Detailed match summary by ID. |
| `GET` | `/matches/{match_id}/timeline` | Detailed round-by-round replay timeline, kills, trades, and Spike events. |
| `DELETE` | `/players/{game_name}/{tag_line}/cache` | Invalidate player snapshot cache on demand. |
| `POST` | `/players/{game_name}/{tag_line}/reports` | Generate a grounded multi-agent coaching report. |
| `GET` | `/players/{game_name}/{tag_line}/reports` | List historical coaching reports for a player. |
| `GET` | `/players/{game_name}/{tag_line}/reports/{id}` | Retrieve a specific coaching report by ID. |

---

## 🤖 Multi-Agent Coaching & Resilient Gemini Integration

### Multi-Agent Framework
Located in `agents/`, the analysis engine operates using dedicated analytical agents:
- **Orchestrator**: Ingests player match telemetry, coordinates sub-agents, and synthesizes structured output.
- **TacticalCoach**: Identifies positioning errors, round win conditions, and map-specific tendencies.
- **EconomyCoach**: Detects buy-round mismatches, force-buy inefficiencies, and save-round discipline.
- **AimCoach**: Evaluates headshot percentages, first-blood conversion, and duel win ratios.
- **AgentSpecificCoach**: Provides tailored playstyle guidance based on agent roles (Duelist, Initiator, Controller, Sentinel).

### Resilient Gemini AI Coach
Located in `frontend/streamlit_app/utils/gemini_coach.py`, the AI coach delivers conversational guidance with production-grade fault tolerance:
- **Automatic Multi-Model Failover Chain**:
  ```text
  gemini-2.5-flash (Primary) ──[Fail]──> gemini-2.5-flash-lite (Fast) ──[Fail]──> gemini-3.5-flash (Fallback)
  ```
- **Exponential Backoff**: Automatic retry schedule (1s, 2s) on transient errors (HTTP 429, 500, 502, 503, 504, connection timeouts).
- **Graceful Error Masking**: User-friendly messaging without leaking HTTP status codes, tracebacks, or credentials.
- **Strict Verification**: Verified by 81 automated resilience tests covering all failure conditions.

---

## 🧪 Quality & Test Verification

The repository maintains strict test coverage, formatting, and linting standards:

```text
565 passed, 0 failures, 0 skips
81/81 Gemini resilience checks passed
100% Ruff & Black compliance
```

### Running the Test Suite

```bash
# Run backend and frontend test suite
uv run --frozen --extra frontend pytest -q tests frontend/streamlit_app/tests

# Run Gemini resilience test suite
uv run --frozen --extra frontend python frontend/streamlit_app/tests/test_gemini_resilience.py

# Check code formatting and linting
uv run --frozen --extra frontend ruff check .
uv run --frozen --extra frontend black --check .
```

---

## 🛠️ Quick Start & Local Setup

### Prerequisites
- **Python 3.12+**
- **uv** (recommended package and project manager)
- **Docker & Docker Compose** (for containerized deployment)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/Siname22/ValorantAICoach.git
cd ValorantAICoach

# Copy sample environment configuration
cp .env.example .env
```

Configure your API keys in `.env`:
```dotenv
# Data Providers (at least one recommended)
HENRIK_API_KEY=your_henrik_key
TRACKER_API_KEY=your_tracker_key
RIOT_API_KEY=your_riot_key

# Google Gemini AI Coach
GEMINI_API_KEY=your_gemini_api_key

# Database (optional for local in-memory development, enabled for production)
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://coach_user:coach_password@localhost:5432/coach_db
```

### 2. Run with Docker Compose (Recommended)

Starts the isolated backend, frontend, and PostgreSQL database:

```bash
docker compose up --build
```

- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Dashboard**: [http://localhost:8501](http://localhost:8501)

### 3. Run Locally with `uv`

#### Start PostgreSQL & Run Migrations:
```bash
# If using local PostgreSQL:
uv run alembic upgrade head
```

#### Start FastAPI Backend:
```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Start Streamlit Frontend:
```bash
uv run --extra frontend streamlit run frontend/streamlit_app/app.py --server.port 8501
```

---

## 📂 Project Structure

```text
ValorantAICoach/
├── agents/                     # Multi-agent tactical analysis framework
│   ├── core/                   # Agent base classes and orchestrators
│   └── specialized/            # Tactical, economy, aim, and agent coaches
├── backend/                    # Core FastAPI backend
│   ├── app/
│   │   ├── api/                # FastAPI routers (auth, players, matches, system)
│   │   ├── core/               # Configuration, settings, and security/JWT
│   │   ├── dependencies/       # Dependency injection providers & auth guards
│   │   ├── schemas/            # Pydantic domain, auth, and response schemas
│   │   ├── services/           # Player, coaching, and auth business logic
│   │   └── storage/            # SQLAlchemy models, Alembic repository & store
│   └── providers/              # External API SDKs (Riot, Henrik, Tracker)
├── database/                   # Alembic database migration scripts
├── docker/                     # Dedicated Dockerfiles for backend and frontend
├── frontend/                   # Interactive Streamlit web application
│   └── streamlit_app/
│       ├── components/         # Reusable UI widgets
│       ├── utils/              # APIClient, Gemini resilient coach, formatters
│       └── tests/              # Frontend unit and resilience tests
├── tests/                      # Backend, auth, provider, persistence, and system tests
├── docker-compose.yml          # Multi-container orchestration
└── pyproject.toml              # UV / Python dependency management
```

---

## 🔮 Roadmap

- [x] Provider SDK abstraction with automatic fallback (Riot, Henrik, Tracker)
- [x] In-memory and PostgreSQL 16 persistence with Alembic migrations
- [x] Automatic snapshot cache expiration and prune endpoint
- [x] Readiness (`/health/ready`) and liveness (`/health/live`) probes
- [x] Multi-agent analytical framework (Tactical, Economy, Aim, Agent-specific)
- [x] Streamlit web dashboard with interactive charts and match viewer
- [x] Interactive Multi-Agent Coaching Report cards and history browser
- [x] Resilient Gemini AI chatbot with 3-model failover and backoff
- [x] Container and dependency isolation (Backend vs Frontend)
- [x] Automated continuous cache pruning background worker
- [x] On-demand player cache invalidation (`DELETE /players/{game}/{tag}/cache`)
- [x] User authentication (PBKDF2-HMAC-SHA256, HS256 JWT bearer tokens)
- [x] Riot player account linking with primary profile selection
- [x] Player progression trajectory analytics & weakness resolution tracking
- [x] Scheduled background coaching sync worker & on-demand sync endpoints
- [x] Computer Vision & OCR integration for in-game scoreboard capture
- [x] Round-by-round replay timeline analysis
- [ ] Team synergy & counter-pick recommendation engine
- [ ] Production deployment hardening, security audit, and Release 1.0

---

## 🤝 Contribution Guidelines

This repository follows a strict review and branch workflow:
1. **Never commit directly to `main` without verified testing**.
2. Create descriptive feature branches (`feature/...`, `fix/...`).
3. Ensure 100% test pass rate (`565+ tests passing`), Ruff, and Black formatting.
4. Submit work via Pull Request with clear release notes.

---

## 📄 License & Intellectual Property

Proprietary. VALORANT and Riot Games are trademarks or registered trademarks of Riot Games, Inc. This project is not endorsed by or affiliated with Riot Games.
