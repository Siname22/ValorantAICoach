# 🎯 Valorant AI Coach

![Valorant AI Coach](assets/banner.png)

> AI-powered coaching platform for VALORANT players built with Clean Architecture, FastAPI and multiple data providers.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Tests](https://img.shields.io/badge/Tests-78%20Passing-success)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 🚀 Overview

Valorant AI Coach is a source-available project that aims to become an intelligent assistant capable of analysing VALORANT matches and helping players improve using Artificial Intelligence.

Unlike traditional stat trackers, this project combines multiple technologies into a single architecture:

- 🎮 Match statistics
- 🤖 Generative AI
- 👁️ Computer Vision
- 📷 OCR
- 📊 Tactical analysis
- 🧠 Personalized coaching

The current focus is building a scalable architecture before implementing advanced AI features.

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
```

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
78 tests passing
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
        routers/
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

This repository is not an open-source project.

If you are collaborating on the project, **do not commit directly to `main`**.

All project work should be performed on a dedicated branch and submitted through a Pull Request. The repository owner reviews changes before they are merged into `main`.

Suggested workflow:

1. Create or use an assigned feature branch.
2. Make commits only on that branch.
3. Push the branch to GitHub.
4. Open a Pull Request against `main`.
5. Wait for review and approval.
6. Only approved changes are merged into `main`.

---

# ⭐ Why this project?

This project is not intended to become "another VALORANT stats tracker".

Its goal is to explore how modern backend architecture can be combined with Artificial Intelligence to build an intelligent coaching platform capable of understanding gameplay and helping players improve.

---

## 📌 Repository

https://github.com/Siname22/ValorantAICoach
