# TN Board Portal — Backend API

Production-ready FastAPI backend for the TN Board Portal, deployed serverlessly on Vercel alongside the Vite/React frontend.

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Server / Runtime | Vercel Serverless (Python runtime) / Uvicorn (local) |
| Database client | Supabase Python SDK |
| Auth | Firebase Admin SDK |
| Config | pydantic-settings |
| Deployment | Vercel (unified monorepo) |

---

## Local Development

### Prerequisites

- Python 3.10+
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
# Edit .env and fill in SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY

# 5. Start the development server
uvicorn app.main:app --reload --port 8000
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Project metadata |
| GET | `/health` | Health check alias |
| GET | `/api/v1/health` | Versioned health check |
| GET | `/api/v1/classes` | Classes list |
| GET | `/api/v1/subjects` | Subjects list |
| GET | `/api/v1/papers` | Papers list |
| GET | `/api/v1/submissions` | Admin submissions list |
| POST | `/api/v1/submissions` | Contributor material submission |
| GET | `/api/v1/leaderboard` | Contributor leaderboard |
| GET | `/api/v1/community/posts` | Community discussions |
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

## Vercel Deployment

The FastAPI backend is served via Vercel Serverless Functions (`api/index.py`).
Root `vercel.json` routes `/api/*`, `/health`, and `/docs` directly to the FastAPI app.

### Environment Variables in Vercel Dashboard

Configure the following variables under **Vercel Dashboard → Project Settings → Environment Variables**:

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase service role key (for server-side ops) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅ | Complete JSON string of Firebase service account |
| `ADMIN_EMAIL` | ✅ | Authorized super admin Google email address |
| `ENVIRONMENT` | ⬜ | `production` / `preview` |
| `LOG_LEVEL` | ⬜ | `INFO` |

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
Supabase (PostgreSQL + Storage) / Firebase Auth
```
