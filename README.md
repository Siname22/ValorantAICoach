# ValorantAICoach
Open-source AI-powered Valorant analytics platform with automated match collection, player profiling, team insights, and coaching recommendations.

## Streamlit Cloud Deployment

This project is prepared for deployment on [Streamlit Community Cloud](https://streamlit.io/cloud). Only the Streamlit frontend is deployed there; the FastAPI backend is hosted separately and consumed over HTTP.

### Deployment Configuration

| Setting | Value |
| --- | --- |
| Repository | `Siname22/ValorantAICoach` (or your fork) |
| Branch | `develop` (or your current working branch) |
| Main file path | `frontend/streamlit_app/app.py` |
| Python version | `3.12` |
| Dependencies file | `requirements.txt` (repository root) |

Streamlit Community Cloud installs dependencies from the root `requirements.txt`. It does **not** resolve `pyproject.toml` or `uv.lock`, so the root requirements file deliberately contains frontend-only packages (`streamlit`, `requests`, `plotly`, `pandas`). Backend dependencies remain declared in `pyproject.toml` and are managed locally with `uv`.

### Installation

Local frontend-only setup:

```bash
# From the repository root
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Full project setup managed with `uv`:

```bash
uv sync
```

### Secrets Configuration

The frontend only needs the base URL of the running FastAPI backend. No provider API keys (Riot, Tracker) are ever exposed to the Streamlit layer.

Local development: copy the template and fill in your value.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
# .streamlit/secrets.toml
VALORANT_API_BASE_URL = "http://127.0.0.1:8000"
```

Streamlit Community Cloud: open the app dashboard, go to **Settings → Secrets** and paste:

```toml
VALORANT_API_BASE_URL = "https://your-backend-domain.example.com"
```

The resolution order implemented in `frontend/streamlit_app/utils/config.py` is Streamlit secrets, then the `VALORANT_API_BASE_URL` environment variable, then the local default `http://127.0.0.1:8000`. The file `.streamlit/secrets.toml` is git-ignored; only the `.example` template is versioned.

### Local Execution

```bash
# From the repository root
streamlit run frontend/streamlit_app/app.py
```

The app is served at `http://localhost:8501`. To exercise live player data, run the FastAPI backend in parallel:

```bash
uvicorn backend.main:app --reload --port 8000
```

### Deployment Steps

1. Push the branch containing the frontend to GitHub.
2. Sign in to [share.streamlit.io](https://share.streamlit.io) with the GitHub account owning the repository.
3. Select **Create app → Deploy a public app from GitHub**.
4. Fill in repository, branch and the main file path `frontend/streamlit_app/app.py`.
5. Under **Advanced settings**, select Python `3.12` and paste the secrets shown above.
6. Click **Deploy** and monitor the build log until the app boots.
