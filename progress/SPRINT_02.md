# Sprint 02 — Backend Foundation (FastAPI)

> **Status:** COMPLETE  
> **Branch:** `dev`  
> **Build:** ✅ 0 errors · backend starts · /health works · / works

---

## Goal

Create a production-ready FastAPI backend foundation for the TN Board Portal.
No business logic migrated. No frontend changes. No database schema changes.
Pure scaffolding that will serve as the base for all future backend sprints.

---

## Architecture

### Current (Sprint 01)
```
React + Vite
    ↓
Supabase JS Client
    ↓
Supabase (PostgreSQL + Storage)
```

### Target (Post Sprint 02 foundation)
```
React (Vercel)
    ↓
FastAPI (Render)
    ↓
Supabase PostgreSQL
Supabase Storage
    ↓
Firebase Authentication (Sprint 05+)
```

### Clean Architecture — Data Flow
```
HTTP Request
    │
    ▼
Route  (app/api/v1/endpoints/)
    │  Validates input, calls service
    ▼
Service  (app/services/)
    │  Business logic — independently testable
    ▼
Repository  (app/repositories/)
    │  Data access — abstracts Supabase calls
    ▼
Supabase (PostgreSQL + Storage)
```

---

## Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          ← FastAPI app factory + CORS + logging + root route
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py                ← v1 route aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py            ← GET /health
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                  ← pydantic-settings Settings class
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase_client.py           ← Supabase singleton (anon + admin)
│   ├── dependencies/
│   │   └── __init__.py                  ← FastAPI DI placeholder
│   ├── middleware/
│   │   └── __init__.py                  ← Custom middleware placeholder
│   ├── models/
│   │   └── __init__.py                  ← SQLAlchemy models placeholder
│   ├── repositories/
│   │   └── __init__.py                  ← Data access layer placeholder
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── health.py                    ← HealthResponse Pydantic model
│   │   └── root.py                      ← RootResponse Pydantic model
│   ├── services/
│   │   ├── __init__.py
│   │   └── health_service.py            ← Health business logic
│   └── utils/
│       └── __init__.py                  ← Shared utilities placeholder
├── scripts/
│   └── __init__.py                      ← Utility scripts placeholder
├── tests/
│   ├── __init__.py
│   └── test_health.py                   ← Health + root endpoint tests
├── .env.example                         ← Environment variable template
├── Dockerfile                           ← python:3.12-slim, non-root user
├── README.md                            ← Setup + deploy documentation
├── render.yaml                          ← Render Blueprint config
└── requirements.txt                     ← 7 pinned packages
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | — | Anon/public key (RLS-protected) |
| `SUPABASE_SERVICE_ROLE_KEY` | ⬜ | `""` | Service role key (admin ops only) |
| `ENVIRONMENT` | ⬜ | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | ⬜ | `INFO` | Python log level |
| `DEBUG` | ⬜ | `false` | Enable debug mode |
| `CORS_ORIGINS` | ⬜ | localhost:5173,3000 | Comma-separated allowed origins |
| `BACKEND_URL` | ⬜ | `http://localhost:8000` | Self-reference for inter-service calls |

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Project metadata (name, version, environment) |
| GET | `/health` | Health check → `{"status":"ok","version":"2.0"}` |
| GET | `/api/v1/health` | Versioned health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |
| GET | `/openapi.json` | OpenAPI schema |

---

## Local Setup

```bash
# 1. Enter backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env: set SUPABASE_URL and SUPABASE_ANON_KEY

# 5. Start development server
uvicorn app.main:app --reload --port 8000

# 6. Verify
curl http://localhost:8000/health
curl http://localhost:8000/
```

---

## Docker

```bash
# Build
cd backend
docker build -t tn-board-backend .

# Run
docker run --env-file .env -p 8000:8000 tn-board-backend

# Verify
curl http://localhost:8000/health
# → {"status":"ok","version":"2.0"}
```

---

## Render Deployment

### Step 1 — First deploy
1. Push `dev` branch to GitHub
2. Render Dashboard → **New** → **Blueprint**
3. Point to `backend/render.yaml`
4. Render builds the Docker image automatically

### Step 2 — Set environment variables
In Render Dashboard → your service → **Environment**, add:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (if needed)
- `CORS_ORIGINS` → your Vercel frontend URL
- `BACKEND_URL` → your Render service URL

### Step 3 — Subsequent deploys
Push to `dev` → Render auto-deploys.

### Health check
Render calls `GET /health` every 30 seconds to determine service health.

---

## Dependencies (requirements.txt)

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.0 | API framework |
| `uvicorn[standard]` | 0.30.6 | ASGI server |
| `supabase` | 2.9.1 | Supabase Python SDK |
| `python-dotenv` | 1.0.1 | .env file loading |
| `pydantic-settings` | 2.4.0 | Type-safe settings from env vars |
| `python-multipart` | 0.0.9 | File upload support |
| `httpx` | 0.27.2 | Async HTTP client |

---

## Files Created

```
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/router.py
backend/app/api/v1/endpoints/__init__.py
backend/app/api/v1/endpoints/health.py
backend/app/config/__init__.py
backend/app/config/settings.py
backend/app/db/__init__.py
backend/app/db/supabase_client.py
backend/app/dependencies/__init__.py
backend/app/middleware/__init__.py
backend/app/models/__init__.py
backend/app/repositories/__init__.py
backend/app/schemas/__init__.py
backend/app/schemas/health.py
backend/app/schemas/root.py
backend/app/services/__init__.py
backend/app/services/health_service.py
backend/app/utils/__init__.py
backend/scripts/__init__.py
backend/tests/__init__.py
backend/tests/test_health.py
backend/.env.example
backend/Dockerfile
backend/render.yaml
backend/requirements.txt
backend/README.md
progress/SPRINT_02.md                    [THIS FILE]
.gitignore                               [MODIFIED — backend entries added]
```

**No frontend files were modified.**  
**No Supabase migrations were created.**  
**No database schemas were changed.**

---

## Verification Results

```
✓ backend starts           uvicorn app.main:app --reload --port 8000
✓ /health works            {"status":"ok","version":"2.0"}
✓ / works                  {"name":"TN Board Portal API","version":"2.0.0",...}
✓ Docker builds            docker build -t tn-board-backend .
✓ no frontend files changed  git diff --name-only shows only backend/ and progress/
✓ git status clean
```

---

## Sprint 03 Roadmap

Sprint 03 should migrate the **papers** domain as the first API resource.

### Recommended order

1. **Papers repository** — `app/repositories/papers_repository.py`
   - Wraps the existing `search_papers()` Supabase RPC
   - `list_papers()`, `get_paper_by_id()`, `search_papers()`

2. **Papers service** — `app/services/papers_service.py`
   - Calls the repository
   - Applies any business rules (filtering, sorting defaults)

3. **Papers schemas** — `app/schemas/paper.py`
   - `PaperResponse`, `PaperListResponse`, `SearchParams`

4. **Papers endpoint** — `app/api/v1/endpoints/papers.py`
   - `GET /api/v1/papers` — paginated list
   - `GET /api/v1/papers/{id}` — single paper detail
   - `GET /api/v1/papers/search` — search with filters

5. **File proxy endpoint** (optional)
   - `GET /api/v1/papers/{id}/download` — proxied Supabase Storage URL

6. **Tests** — `tests/test_papers.py`

### After papers
- Subjects endpoint
- Classes endpoint
- Upload endpoint (with multipart/form-data)
- Authentication (Sprint 05: Firebase)
- Admin dashboard APIs (Sprint 06+)
