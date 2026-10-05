# 🎯 Valorant AI Coach

![Valorant AI Coach](assets/banner.png)

> AI-powered coaching platform for VALORANT players built with Clean Architecture, FastAPI and multiple data providers.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Tests](https://img.shields.io/badge/Tests-pytest-success)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Overview

Valorant AI Coach is an open-source platform that aims to become an intelligent assistant capable of analysing VALORANT matches and helping players improve using Artificial Intelligence.

Unlike traditional stat trackers, this project combines multiple technologies into a single architecture:

- 🎮 Match statistics
- 🤖 Generative AI
- 👁️ Computer Vision
- 📷 OCR
- 📊 Tactical analysis
- 🧠 Personalized coaching

The current focus is building a scalable architecture before implementing advanced AI features.

## Local Setup (0.4.0)

Python 3.12+ and `uv` are required. From the repository root:

```powershell
uv sync --frozen
Copy-Item .env.example .env
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open [API documentation](http://127.0.0.1:8000/docs). The backend also starts
without `.env` or API keys: `/health/live` returns `ok`, `/health` reports
disabled providers, and player queries return `503` until a supported provider
is configured. PostgreSQL is not required for the current player endpoints.

Set one or more keys in `.env`: `HENRIK_API_KEY`, `TRACKER_API_KEY`, or
`RIOT_API_KEY`. Restart the backend after changing provider configuration.
An empty key or `<PROVIDER>_ENABLED=false` disables that provider; malformed
configuration is reported as `misconfigured`. Keys are not included in API errors.

- Henrik supplies account identity, current rank/RR and stored match summaries.
  Match queries resolve the account region, or accept `?region=eu` explicitly.
  Stored history may be incomplete; it is not a complete live match archive.
- Tracker supplies profiles, rank and recent matches, subject to API access.
- Riot uses real account-v1 and val-match-v1 requests. Match access depends on
  the permissions of the supplied key. It does not expose a player's current
  rank/RR. `RIOT_REGION` selects the match shard; `RIOT_BASE_URL` must be a shard
  host without an API path. Set `RIOT_ACCOUNT_BASE_URL` independently to the
  appropriate continental account host (`europe`, `americas` or `asia`).

The example configuration targets Europe. Riot summaries preserve official map
and character identifiers; their conversion to display names is still pending.
Timestamps retain each provider's format: Riot milliseconds, Henrik/Tracker
date strings. Match summaries include `provider` provenance. Henrik's stored
`score` has no documented total/average meaning, so its `score` is `null` and the
original value is preserved in `provider_score`; do not compare that value with
total scores. See the [stored-match guide](https://docs.henrikdev.xyz/valorant/guides/stored-matches.md)
and [OpenAPI contract](https://api.henrikdev.xyz/openapi.json).
Tests simulate provider HTTP responses; live credentials are
required to verify access against the external APIs.

For Docker:

```powershell
docker compose up --build
```

Compose passes provider credentials/configuration to the backend and uses
`/health/live` for its health check. `httpx` is a runtime dependency, so the
production image does not require development packages.

---

# ✨ Current Features

## Multi Provider SDK

Supports multiple providers through a common abstraction layer.

Current providers:

- Riot API
- HenrikDev API
- Tracker.gg

Future providers can be added without changing business logic.

---

## Player Service

Unified service responsible for obtaining player information.

Features:

- Automatic provider fallback
- Dependency Injection
- Provider abstraction
- Unified domain models

```
Tracker
   ↓
Henrik
   ↓
 Riot
```

If one provider fails, the next one is automatically used.

---

## REST API

FastAPI endpoints already implemented.

Examples:

```
GET /players/{gameName}/{tagLine}

GET /players/{gameName}/{tagLine}/rank

GET /players/{gameName}/{tagLine}/matches

GET /players/{gameName}/{tagLine}/matches?region=eu&limit=5

GET /matches/{matchId}

GET /health

GET /health/live
```

The match limit is 1-20 (default 10). `/matches/{matchId}` returns the full Riot
match payload and requires the Riot provider on the appropriate shard.
`404` means every applicable provider confirmed absence. Provider outages,
missing credentials and unsupported data capabilities return `503`; malformed
upstream responses return `502`; a confirmed
empty match history returns `200` with `matches: []`. Invalid input returns `422`.

---

## Architecture

```
                FastAPI
                   │
           REST Controllers
                   │
            Player Service
                   │
      ┌────────────┼────────────┐
      │            │            │
   Tracker      Henrik        Riot
      │            │            │
      └──────── Providers ──────┘
```

The project follows:

- Clean Architecture
- SOLID principles
- Dependency Injection
- Provider Pattern
- Repository-like abstraction
- Service Layer

---

# 🧪 Quality

Current automated tests:

- Provider SDK
- Riot Provider
- Henrik Provider
- Tracker Provider
- PlayerService
- Agent Framework
- REST endpoints

```
uv run pytest
uv run ruff check .
```

Code quality:

- Ruff
- Black
- Pytest

---

# 📂 Project Structure

```
backend/
    app/
        api/
        services/
        dependencies/

    providers/
        riot/
        tracker/
        henrik/

agents/

tests/

docs/
```

---

# 🔮 Roadmap

Current progress

- ✅ Provider SDK
- ✅ Tracker Provider
- ✅ Riot Provider
- ✅ Henrik Provider
- ✅ Player Service
- ✅ FastAPI REST API

Next milestones

- OCR integration
- Screenshot analysis
- Computer Vision
- Match timeline analysis
- AI tactical reports
- LLM coaching
- Agent memory
- Web frontend
- Authentication

---

# 🛠️ Tech Stack

Backend

- Python
- FastAPI
- Pydantic
- Pytest

Architecture

- Clean Architecture
- SOLID
- Dependency Injection

External APIs

- Riot Games API
- HenrikDev API
- Tracker.gg

Future AI

- OpenAI
- Gemini
- Claude
- Local LLMs

---

# 🤝 Contributing

Contributions, ideas and feedback are always welcome.

If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Open a Pull Request

---

# ⭐ Why this project?

This project is not intended to become "another VALORANT stats tracker".

Its goal is to explore how modern backend architecture can be combined with Artificial Intelligence to build an intelligent coaching platform capable of understanding gameplay and helping players improve.

---

## 📌 Repository

https://github.com/Siname22/ValorantAICoach
