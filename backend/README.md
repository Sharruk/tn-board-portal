# TN Board Portal — Backend API

Production-ready FastAPI backend for the TN Board Portal.

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Server | Uvicorn (ASGI) |
| Database client | Supabase Python SDK |
| Config | pydantic-settings |
| Container | Docker (python:3.12-slim) |
| Deployment | Render |

---

## Local Development

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your local .env file
cp .env.example .env
# Edit .env and fill in SUPABASE_URL and SUPABASE_ANON_KEY

# 5. Start the development server
uvicorn app.main:app --reload --port 8000
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Project metadata |
| GET | `/health` | Health check (used by Render) |
| GET | `/api/v1/health` | Versioned health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

## Running Tests

```bash
cd backend
pip install pytest
pytest tests/ -v
```

---

## Docker

### Build

```bash
cd backend
docker build -t tn-board-backend .
```

### Run

```bash
docker run --env-file .env -p 8000:8000 tn-board-backend
```

### Test the container

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"2.0"}

curl http://localhost:8000/
# → {"name":"TN Board Portal API","version":"2.0.0",...}
```

---

## Render Deployment

### First Deploy

1. Push this repo to GitHub (on `dev` branch)
2. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. Connect your GitHub repo and select `backend/render.yaml`
4. Render will detect the Dockerfile and create the service

### Environment Variables

After the service is created, set these in **Render Dashboard → Environment**:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API |
| `CORS_ORIGINS` | Your Vercel frontend URL |
| `BACKEND_URL` | Your Render service URL (after first deploy) |

### Subsequent Deploys

Push to `dev` branch → Render auto-deploys.

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py      ← GET /health
│   │       └── router.py          ← v1 route aggregator
│   ├── config/
│   │   └── settings.py            ← pydantic-settings Settings class
│   ├── db/
│   │   └── supabase_client.py     ← Supabase singleton
│   ├── dependencies/              ← FastAPI DI (future)
│   ├── middleware/                ← Custom middleware (future)
│   ├── models/                    ← SQLAlchemy models (future)
│   ├── repositories/              ← Data access layer (future)
│   ├── schemas/
│   │   ├── health.py              ← HealthResponse model
│   │   └── root.py                ← RootResponse model
│   ├── services/
│   │   └── health_service.py      ← Health business logic
│   └── main.py                    ← FastAPI app factory
├── scripts/                       ← Utility scripts (future)
├── tests/
│   └── test_health.py
├── .env.example                   ← Environment variable template
├── Dockerfile
├── README.md
├── render.yaml                    ← Render deployment config
└── requirements.txt
```

---

## Architecture

```
Request
  │
  ▼
Route (app/api/v1/endpoints/)
  │  Thin — validates input, calls service
  ▼
Service (app/services/)
  │  Business logic — testable independently
  ▼
Repository (app/repositories/)
  │  Data access — abstracts Supabase calls
  ▼
Supabase (PostgreSQL + Storage)
```

---

## Environment Variables

See [.env.example](.env.example) for the full list with descriptions.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | — | Supabase anon key (RLS-protected) |
| `SUPABASE_SERVICE_ROLE_KEY` | ⬜ | `""` | Service role key (admin ops) |
| `ENVIRONMENT` | ⬜ | `development` | Runtime environment |
| `LOG_LEVEL` | ⬜ | `INFO` | Python logging level |
| `DEBUG` | ⬜ | `false` | Enable debug mode |
| `CORS_ORIGINS` | ⬜ | localhost | Comma-separated allowed origins |
| `BACKEND_URL` | ⬜ | localhost:8000 | Backend self-reference URL |
