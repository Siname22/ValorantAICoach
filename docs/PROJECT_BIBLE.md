# Valorant AI Coach: Project Bible

> **Single Source of Truth** for technical architecture, domain rules, security standards, operational guarantees, and coding guidelines for the Valorant AI Coach platform.

---

## 1. Vision & Core Philosophy

**Valorant AI Coach** is a specialized, production-ready analytics and tactical coaching platform for VALORANT players. Unlike static statistics viewers, it analyzes player match telemetry across combat, economy, and agent role execution, synthesizing actionable, evidence-based recommendations.

### Guiding Principles
1. **Zero Hallucination / No Synthetic Fallbacks**: Player metrics and scoreboard reads must be truthful. If external APIs or vision models fail, the platform explicitly reports an error (HTTP 422, 502, or 503) rather than inventing statistics.
2. **Provider Agnosticism**: Tactical analysis and presentation layers operate exclusively on normalized internal domain models (`PlayerProfile`, `PlayerMatch`, `PlayerStatsOverview`). Upstream providers (Riot, HenrikDev, Tracker.gg) are abstracted behind strict interfaces.
3. **Decoupled Architecture**: Backend (FastAPI) and Frontend (Streamlit) run in fully isolated environments with independent virtual environments, dependency manifests, and lifecycle management. The frontend communicates with the backend strictly over HTTP REST.
4. **Security by Default**: All mutating and resource-heavy endpoints (AI coaching report generation, match synchronization, scoreboard vision ingestion, cache invalidation, cache pruning) require cryptographic authentication. Administrative maintenance endpoints require admin authorization.

---

## 2. System Architecture

```text
                                  ┌─────────────────────────────────────────┐
                                  │      Streamlit Frontend (Port 8501)     │
                                  │   (Isolated Container & Dependencies)   │
                                  └────────────────────┬────────────────────┘
                                                       │ HTTP REST (JWT Bearer)
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │        FastAPI Backend (Port 8000)      │
                                  │   (Clean Architecture / Service Layer)  │
                                  └─────────┬───────────────────┬───────────┘
                                            │                   │
                           ┌────────────────┴──────────┐        │ Multi-Agent
                           ▼                           ▼        ▼
                 ┌──────────────────┐       ┌──────────────────────┐
                 │  SQLPlayerStore  │       │  Multi-Agent System  │
                 │  (PostgreSQL 16) │       │ (Analyst/Econ/Role)  │
                 └──────────────────┘       └──────────────────────┘
                           │
                 ┌─────────┴─────────┬──────────────────┐
                 ▼                   ▼                  ▼
          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
          │  Tracker.gg  │   │  HenrikDev   │   │  Riot Games  │
          └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 3. Core Modules & Responsibilities

### 3.1 Backend (`backend/`)
- `backend/app/api/`: REST API routers (`auth_router`, `player_router`, `match_router`, `vision_router`, `synergy_router`).
- `backend/app/core/`: Configuration settings (`config.py`), cryptographic primitives (`security.py`), and error definitions.
- `backend/app/dependencies/`: FastAPI dependency injection (`auth_deps.py`, `provider_deps.py`).
- `backend/app/middleware/`: Production security headers (`SecurityHeadersMiddleware`) and payload size defense (`ContentLengthLimitMiddleware`).
- `backend/app/schemas/`: Pydantic V2 domain and request/response schemas.
- `backend/app/services/`: Core application business logic (`player_service.py`, `vision_service.py`, `timeline_service.py`, `synergy_service.py`).
- `backend/app/storage/`: SQLAlchemy 2.0 ORM models, Alembic migrations repository, and PostgreSQL/SQLite persistence (`SQLPlayerStore`).
- `backend/providers/`: Upstream SDK clients (`RiotProvider`, `HenrikProvider`, `TrackerProvider`).

### 3.2 Multi-Agent Engine (`agents/`)
Specialized analytical agents orchestrated to generate structured coaching reports:
- `orchestrator`: Ingests match telemetry, coordinates sub-agents, and synthesizes the unified training plan.
- `match_analyst`: Evaluates combat, duels, opening kills, trade kills, and round win conditions.
- `economy_coach`: Evaluates buy-round discipline, force-buys, eco-round conversions, and loadout mismatches.
- `role_coach`: Evaluates agent-specific utility usage, ability timings, and role fulfillment (Duelist, Initiator, Controller, Sentinel).
- `report_writer`: Formulates natural language summaries, actionable drills, and evidence tables.

### 3.3 Frontend (`frontend/`)
- Interactive Streamlit dashboard consuming the headless FastAPI backend.
- Resilient Gemini AI Coach integration with automatic 3-model failover chain (`gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-3.5-flash`) and exponential backoff.
- Interactive modules: Player Search, Replay Timeline Explorer, Scoreboard Vision Ingest, Trajectory Evolution, Team Synergy & Counter-Picks, and Resilient Chat.

---

## 4. Security & Cryptography Standards

1. **Password Storage**: Passwords are hashed using **Argon2id** (`argon2-cffi`). Legacy PBKDF2-HMAC-SHA256 hashes are automatically upgraded to Argon2id upon valid login.
2. **Access Tokens**: RFC 7519 JWT access tokens signed with HMAC-SHA256 (`HS256`). Mandatory claims: `sub`, `exp`, `iat`. Tokens missing expiration or subject are strictly rejected.
3. **Secret Key Validation**: Outside development/test environments, `JWT_SECRET_KEY` must be explicitly configured with at least 32 characters; application startup aborts if missing.
4. **Role-Based Access Control**:
   - General mutators (`/players/.../reports`, `/players/.../sync`, `/vision/...`) require active authenticated user tokens (`get_current_user`).
   - System maintenance endpoints (`/system/cache/prune`, `/system/coaching/sync-tracked`) require administrative authorization (`require_admin`), verified via `is_admin` database flag or `ADMIN_EMAILS` environment configuration.
5. **HTTP Defense**:
   - Security Headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and strict `Content-Security-Policy`.
   - Payload Limit: Requests exceeding `MAX_REQUEST_BODY_SIZE_BYTES` (25 MB) are terminated with HTTP 413.
   - Non-root Container Execution: Both backend and frontend Docker containers run under dedicated unprivileged `appuser` (UID/GID 10001).

---

## 5. Development & Code Hygiene

- **Code Formatting & Linting**: 100% compliant with **Black** (88-character line limit) and **Ruff**.
- **Package Management**: **uv** is the designated package and virtual environment manager across local development, Docker builds, and CI pipelines.
- **Git Hygiene**: Clean working directory, feature-branch workflows, and no cache files or virtual environments checked into version control.
