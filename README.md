# Valorant AI Coach

![Valorant AI Coach](assets/banner.png)

> Professional AI-powered coaching and intelligence platform for VALORANT players built with Clean Architecture, FastAPI, PostgreSQL, Multi-Agent analysis, and resilient Google Gemini integration.

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Angular-19-DD0031)](https://angular.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-success)](https://pytest.org/)
[![WCAG](https://img.shields.io/badge/A11y-WCAG%202.2%20AA-brightgreen)](https://www.w3.org/WAI/standards-guidelines/wcag/)
[![Release](https://img.shields.io/badge/Release-v1.0.0-blueviolet)](https://github.com/Siname22/ValorantAICoach/releases)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-red)](https://github.com/astral-sh/ruff)

---

## 🚀 Overview

**Valorant AI Coach** is an advanced analytics and intelligent coaching platform designed to elevate VALORANT player performance. Rather than acting as a static statistics viewer, the platform combines robust backend engineering, multi-provider data aggregation, persistent domain models, multi-agent tactical analysis, and a resilient generative AI coaching assistant.

### Key Pillars
- **Unified Multi-Provider Aggregation**: Transparent fallback across Tracker.gg, HenrikDev, and Riot Games APIs with automatic circuit breaking and error isolation.
- **Enterprise Persistence**: Production PostgreSQL 16 database managed via Alembic migrations, supporting atomic snapshot caching, player histories, coaching reports, and user identities.
- **User Authentication & Linked Accounts**: Secure PBKDF2-HMAC-SHA256 password hashing, cryptographically signed HS256 JWT access tokens, and multi-identity Riot player account linking with primary profile selection.
- **Backend & Frontend Isolation**: Headless FastAPI service and modern Angular 19 HUD Bento SPA run in fully decoupled containers with independent dependencies and environments.
- **Grounded Multi-Agent Coaching**: Specialized agents evaluate player telemetry (Aim, Economy, Positioning, Agent Utility) and compile structured, evidence-backed recommendations.
- **Resilient AI Vision & Coach**: Integrated Google Gemini assistant powered by the official SDK for scoreboard screenshot analysis, multi-agent reporting, and tactical guidance.
- **Team Synergy & Counter-Pick Engine**: Tactical composition evaluation providing squad archetype synergy scores, utility coverage breakdown, and opponent-tailored counter-pick guidance.
- **Production Hardened & Audited**: Robust security headers (CSP, HSTS, frame protection, MIME sniffing protection), configurable CORS, request body size limits against DoS, and non-root Docker execution.

---

## 🏗️ Architecture & Component Isolation

The platform enforces strict separation of concerns across service boundaries:

```text
                        ┌─────────────────────────────────────────┐
                        │     Angular HUD Bento SPA (Port 8080)   │
                        │   (Nginx Container / WCAG 2.2 AA)       │
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
1. **Frontend Isolation**: The frontend communicates with the backend solely over HTTP via the generated TypeScript OpenAPI client. It maintains zero direct database or internal service bindings.
2. **Container Separation**: `docker/backend.Dockerfile` and `docker/frontend.Dockerfile` build isolated images (Python 3.12 backend and Node 22/Nginx 1.27 SPA frontend), eliminating dependency pollution.
3. **Test Isolation**: Backend unit tests run with zero frontend dependencies. Frontend testing and static builds run independently in the Angular workspace.
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
| `POST` | `/recommendations/composition/synergy` | Evaluate squad agent synergy, role balance, and utility coverage. |
| `POST` | `/recommendations/counter-picks` | Calculate top agent counter-picks against an enemy lineup on a specific map. |
| `GET` | `/players/{game_name}/{tag_line}/counter-picks` | Personalized counter-pick recommendations tailored to player agent pool. |

---

## 🤖 Multi-Agent Coaching & Resilient Gemini Integration

### Multi-Agent Framework
Located in `agents/`, the analysis engine operates using dedicated analytical agents:
- **orchestrator**: Coordinates the analysis lifecycle, ingests player match telemetry, invokes sub-agents, and compiles the unified training plan.
- **match_analyst**: Evaluates combat performance, duel win rates, opening duels, and trade efficiency.
- **economy_coach**: Detects buy-round mismatches, force-buy inefficiencies, and save-round discipline.
- **role_coach**: Provides role execution insights tailored to agent classes (Duelist, Initiator, Controller, Sentinel).
- **report_writer**: Synthesizes natural-language feedback, evidence tables, and targeted training routines.

### Resilient Gemini AI Integration
The AI engine integrates Google Gemini with production-grade fault tolerance:
- **Automatic Multi-Model Failover Chain**:
  ```text
  gemini-2.5-flash (Primary) ──[Fail]──> gemini-2.5-flash-lite (Fast) ──[Fail]──> gemini-3.5-flash (Fallback)
  ```
- **Exponential Backoff**: Automatic retry schedule (1s, 2s) on transient errors (HTTP 429, 500, 502, 503, 504, connection timeouts).
- **Graceful Error Masking**: User-friendly messaging without leaking HTTP status codes, tracebacks, or credentials.
- **Multimodal Scoreboard Vision**: Vision OCR processing of in-game match screenshots with structured JSON output and schema validation.

---

## 🧪 Quality & Test Verification

The repository maintains strict test coverage, formatting, and linting standards:

- Comprehensive regression test suites covering API routes, security, persistence, vision, and agents.
- 100% Ruff and Black compliance with strict 88-character line limits.
- Full TypeScript strict typing and WCAG 2.2 AA accessibility validation in Angular.

### Running the Backend Test Suite

```bash
# Run backend regression tests
uv run pytest -q tests

# Check code formatting and linting
uv run ruff check .
uv run black --check .
```

### Running the Frontend Angular Application

```bash
cd frontend/web
npm install
npm run build
npm start
```

---

## 🛠️ Quick Start & Local Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 22+** & **npm**
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
- **Frontend Dashboard (Angular HUD Bento)**: [http://localhost:8080](http://localhost:8080)

### 3. Run Locally with `uv` and `npm`

#### Start PostgreSQL & Run Migrations:
```bash
# If using local PostgreSQL:
uv run alembic upgrade head
```

#### Start FastAPI Backend:
```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Start Angular HUD Bento Frontend:
```bash
cd frontend/web
npm install
npm start
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
├── frontend/                   # Frontend SPA client
│   └── web/                    # Angular 19 HUD Bento SPA (WCAG 2.2 AA, signals)
│       ├── src/app/core/       # API client generated from OpenAPI, auth, tokens
│       ├── src/app/features/   # Dashboard, Search, Reports, Matches, Vision
│       └── src/app/shared/     # Bento cards, HUD navigation, SVG radar charts
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
- [x] Angular 19 HUD Bento SPA with WCAG 2.2 AA accessibility
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
- [x] Team synergy & counter-pick recommendation engine
- [x] Production deployment hardening, security audit, and Release 1.0

---

## 🔒 Production Security & Hardening

The platform adheres to enterprise-grade security standards:
- **OWASP Recommended Security Headers**: Automatic injection of `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), camera=(), microphone=()`, and hardened `Content-Security-Policy`.
- **Strict-Transport-Security (HSTS)**: Configurable HSTS enforcement with `includeSubDomains` for production environments.
- **Controlled CORS Policy**: Explicitly configured allowed origins prevents arbitrary domain cross-site access.
- **Request Body Size Guard**: `ContentLengthLimitMiddleware` terminates requests exceeding maximum body thresholds (default 25 MB) with HTTP 413 to prevent memory exhaustion and DoS vectors.
- **Least-Privilege Docker Containers**: Containers run under dedicated unprivileged `appuser` (UID/GID 10001) with internal container health checks.

---

## 🤝 Contribution Guidelines

This repository follows a strict review and branch workflow:
1. **Never commit directly to `main` without verified testing**.
2. Create descriptive feature branches (`feature/...`, `fix/...`).
3. Ensure 100% test pass rate (`581+ tests passing`), Ruff, and Black formatting.
4. Submit work via Pull Request with clear release notes.

---

## 📄 License & Intellectual Property

Proprietary. VALORANT and Riot Games are trademarks or registered trademarks of Riot Games, Inc. This project is not endorsed by or affiliated with Riot Games.
