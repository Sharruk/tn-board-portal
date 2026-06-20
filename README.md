# TN State Board Learning Platform

A production-ready portal for Tamil Nadu State Board students to access question papers and answer keys for Classes 9–12. Admins manage content through a secure JWT-protected dashboard.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                     Browser                      │
│          React 18 + Vite 5 + Tailwind CSS        │
│      Public portal  │  Admin dashboard (JWT)     │
└──────────┬──────────┴──────────────┬─────────────┘
           │ /api/v1/*  (proxied)    │ PDF links
           ▼                         ▼
┌──────────────────────┐   ┌──────────────────────┐
│     FastAPI           │   │   File Storage        │
│   (Python 3.11+)     │   │  local  (dev)         │
│                       │   │  Supabase CDN (prod)  │
│  classes / subjects   │   └──────────────────────┘
│  papers / auth        │
│  admin / search       │
│  rate_limit / audit   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL Database  │
│  classes, subjects,   │
│  papers, admins,      │
│  audit_logs           │
└──────────────────────┘
```

---

## Tech Stack

| Layer      | Technology                                  |
|------------|---------------------------------------------|
| Frontend   | React 18, Vite 5, Tailwind CSS 3, Axios     |
| Backend    | FastAPI, Uvicorn, Python 3.11+              |
| ORM        | SQLAlchemy 2.x                              |
| Database   | PostgreSQL 14+                              |
| Auth       | JWT (PyJWT), Werkzeug password hashing      |
| Storage    | Local filesystem (dev) / Supabase (prod)    |
| Container  | Docker / Docker Compose                     |

---

## Folder Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (classes, subjects, papers, auth, admin)
│   │   ├── database/       # SQLAlchemy engine + session factory
│   │   ├── models/         # ORM models: Class, Subject, Paper, Admin, AuditLog
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # auth, storage, rate_limit, audit, analytics
│   │   ├── config.py       # Environment variable loading + validation
│   │   └── main.py         # FastAPI app entry point
│   ├── Dockerfile          # Backend container
│   ├── requirements.txt    # Python dependencies
│   ├── seed.py             # Populate DB: classes, subjects, default admin
│   └── migrate_41.py       # One-time schema migration utility
├── frontend/
│   ├── src/
│   │   ├── components/     # Shared UI components
│   │   ├── contexts/       # AuthContext (JWT state)
│   │   ├── hooks/          # Custom hooks
│   │   ├── layouts/        # Page shell layouts
│   │   ├── pages/          # Public + admin pages
│   │   ├── router/         # React Router v6 definitions
│   │   └── services/       # Axios API clients
│   ├── index.html
│   ├── package.json
│   └── vite.config.js      # Dev server + API proxy config
├── docker-compose.yml       # Local dev stack (db + backend + frontend)
├── .env.example             # Environment variable template (never commit .env)
├── change_admin_password.py # Interactive admin credential updater
└── uploads/                 # Local PDF storage (dev only — ephemeral in prod)
```

---

## Environment Variables

See `.env.example` for a fully annotated list. Minimum required:

| Variable                    | Required         | Notes                                      |
|-----------------------------|------------------|--------------------------------------------|
| `DATABASE_URL`              | Yes              | `postgresql://user:pass@host:5432/dbname`  |
| `JWT_SECRET_KEY`            | Yes              | 32+ random chars — generate with `secrets` |
| `ENVIRONMENT`               | No (development) | `development` or `production`              |
| `CORS_ORIGINS`              | Yes in prod      | Comma-separated allowed origins            |
| `STORAGE_BACKEND`           | No (local)       | `local`, `supabase`, or `s3`              |
| `SUPABASE_URL`              | If supabase      | `https://<project>.supabase.co`            |
| `SUPABASE_SERVICE_ROLE_KEY` | If supabase      | Service role key (not anon key)            |
| `SUPABASE_BUCKET`           | No (papers)      | Supabase storage bucket name               |

---

## Local Setup

### Prerequisites
- Python 3.11+, Node.js 20+, PostgreSQL 14+

### 1 — Configure environment
```bash
cp .env.example .env
# Edit .env — set DATABASE_URL and JWT_SECRET_KEY
```

### 2 — Backend
```bash
cd backend
pip install -r requirements.txt
python seed.py          # create tables + seed classes/subjects/admin
uvicorn app.main:app --reload --port 8000
```

### 3 — Frontend
```bash
cd frontend
npm install
npm run dev             # http://localhost:5000 (proxies /api to :8000)
```

API docs: `http://localhost:8000/docs`
Admin login: `http://localhost:5000/admin/login`

**Change the default admin password immediately:**
```bash
python change_admin_password.py
```

---

## Production Deployment

### Docker Compose (self-hosted)
```bash
docker compose up --build -d
```

### Railway (backend) + Vercel (frontend)
See `FINAL_DEPLOYMENT_AUDIT.md` for step-by-step instructions.

---

## Supabase Storage Setup

1. Create a Supabase project → Storage → New bucket named `papers` → set **Public**.
2. Copy **Project URL** and **service_role** key from Settings → API.
3. Set environment variables:
   ```
   STORAGE_BACKEND=supabase
   SUPABASE_URL=https://<project-id>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
   SUPABASE_BUCKET=papers
   ```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `RuntimeError: DATABASE_URL is not set` | Add `DATABASE_URL` to `.env` or secrets |
| `RuntimeError: JWT_SECRET_KEY is still the insecure default` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `RuntimeError: SUPABASE_URL … must be set` | Add Supabase secrets or use `STORAGE_BACKEND=local` |
| `409 Conflict` on upload | Duplicate paper — use a unique title or delete the existing one |
| Login returns 423 Locked | Account locked after 5 failed attempts — wait 15 min or reset via DB |
| CORS error in browser | Add exact frontend origin to `CORS_ORIGINS` |
| PDFs missing after redeploy | Local storage is ephemeral — switch to `STORAGE_BACKEND=supabase` |
