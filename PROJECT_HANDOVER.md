# Project Handover — TN State Board Learning Platform

---

## Current Architecture

```
Browser (React 18 SPA)
    ├── Public portal — Class → Subject → Papers browse
    ├── Search — full-text with alias expansion
    └── Admin dashboard — JWT-protected upload/manage

FastAPI backend (Python 3.11+)
    ├── /api/v1/classes          — list Classes 9-12
    ├── /api/v1/subjects         — list subjects per class
    ├── /api/v1/papers           — papers, search, download tracking
    ├── /api/v1/auth/login       — returns JWT
    └── /api/v1/admin/*          — CRUD + audit logs (JWT required)

PostgreSQL database
    ├── classes       — Class 9, 10, 11, 12
    ├── subjects      — Tamil, English, Maths, Physics, etc.
    ├── papers        — uploaded PDFs with metadata
    ├── admins        — admin accounts with lockout fields
    └── audit_logs    — all admin actions

File storage (pluggable)
    ├── local   — dev only — /uploads/ on local filesystem
    └── supabase — prod — Supabase Storage CDN
```

---

## All Services Used

| Service | Purpose | Required? |
|---------|---------|-----------|
| PostgreSQL 14+ | Primary database | Yes |
| Supabase Storage | PDF file hosting in production | For production uploads |
| Replit PostgreSQL | Database in Replit environment | Replit only |

No third-party auth, no email service, no payment provider, no external APIs.

---

## How to Run Locally

### Quick start (two terminals)

```bash
# Terminal 1 — Backend
cp .env.example .env   # configure DATABASE_URL + JWT_SECRET_KEY
cd backend
pip install -r requirements.txt
python seed.py                              # first run only
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

App: http://localhost:5000
Admin: http://localhost:5000/admin/login (default: admin / admin123 — change immediately)
API docs: http://localhost:8000/docs

### Or with Docker Compose

```bash
cp .env.example .env   # set JWT_SECRET_KEY
docker compose up --build
docker compose exec backend python seed.py   # first run only
```

---

## How to Deploy

### Option A — Replit (current)

- Backend workflow: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Frontend workflow: `cd frontend && npm run dev`
- Secrets: set in Replit Secrets panel
- Database: Replit built-in PostgreSQL (DATABASE_URL auto-provided)
- File storage: set `STORAGE_BACKEND=supabase` with Supabase credentials for persistence

### Option B — Railway (backend) + Vercel (frontend)

**Backend on Railway:**
1. Connect GitHub repo → select `backend/` as root directory
2. Railway auto-detects `Dockerfile`
3. Set environment variables: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS=https://your-vercel-app.vercel.app`, `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET=papers`
4. First deploy: run `railway run python seed.py`

**Frontend on Vercel:**
1. Import repo → set root directory to `frontend/`
2. Framework: Vite, Build: `npm run build`, Output: `dist`
3. Set `VITE_API_BASE_URL=https://your-backend.up.railway.app` (if using absolute URLs)
4. Add `frontend/vercel.json`:
   ```json
   {
     "rewrites": [
       {"source": "/api/:path*", "destination": "https://your-backend.railway.app/api/:path*"},
       {"source": "/(.*)", "destination": "/index.html"}
     ]
   }
   ```

### Option C — Docker Compose (self-hosted VPS)

```bash
docker compose up --build -d
docker compose exec backend python seed.py
```

See `DOCKER_DEPLOYMENT.md` for full details.

---

## Required Accounts

| Account | Purpose | Required for |
|---------|---------|-------------|
| **PostgreSQL access** | Primary database | All environments |
| **Supabase** (supabase.com) | PDF file storage in production | Production uploads |
| **Railway** (railway.app) | Backend hosting | Option B deployment |
| **Vercel** (vercel.com) | Frontend hosting | Option B deployment |
| **GitHub** | Source code hosting | CI/CD, deployment triggers |

---

## Required Secrets

| Secret | How to get | Where to set |
|--------|-----------|-------------|
| `DATABASE_URL` | From your PostgreSQL provider | Secrets manager / Replit Secrets |
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | Secrets manager |
| `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL | Secrets manager |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API → service_role | Secrets manager |

Never commit any of these values to source control.

---

## Known Limitations

| Limitation | Impact | Workaround / Fix |
|-----------|--------|-----------------|
| **In-memory rate limiter** | With multiple backend workers, each worker has an independent IP lockout store — blocked IPs can authenticate through other workers | Use Redis for shared rate limit state |
| **Local file storage is ephemeral** | Files uploaded with `STORAGE_BACKEND=local` are lost on server restart/redeploy | Use `STORAGE_BACKEND=supabase` in production |
| **Single admin role** | No role hierarchy — all admins have full access | Add role-based access control if multiple admin users are needed |
| **No refresh tokens** | JWT access tokens expire after `JWT_EXPIRE_MINUTES` (default 60) — admin must re-login | Implement refresh token flow |
| **S3 provider is a stub** | `STORAGE_BACKEND=s3` raises `NotImplementedError` | Implement `S3StorageProvider` in `backend/app/services/storage.py` |
| **No email notifications** | No alerts for new uploads, failed logins, etc. | Integrate SendGrid/Mailgun if needed |
| **No CDN for local uploads** | Local PDFs served directly from FastAPI `/uploads/` — slow for large files | Use Supabase (includes CDN) or CloudFront |
| **pyproject.toml has legacy deps** | Extra packages installed in Replit environment | Fixed: removed in this audit |

---

## Future Roadmap

### High Priority
- [ ] Replace in-memory rate limiter with Redis for multi-worker safety
- [ ] Add refresh token support to avoid frequent admin re-logins
- [ ] Implement RBAC (read-only admin, super-admin)
- [ ] Add pagination to paper listings (currently returns all results)

### Medium Priority
- [ ] Implement AWS S3 storage provider
- [ ] Add bulk delete for papers
- [ ] Add paper visibility toggle from the list view (currently requires edit dialog)
- [ ] Add email notification for failed login bursts
- [ ] Set up CI/CD pipeline (GitHub Actions)

### Low Priority
- [ ] Add student-facing comment/rating system
- [ ] Implement PDF preview in browser (instead of download only)
- [ ] Add analytics dashboard for most-downloaded papers
- [ ] Dark mode for public portal
- [ ] Multilingual support (Tamil / English)

---

## File Index

| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app factory, CORS, routers, SPA fallback |
| `backend/app/config.py` | All env var loading + validation |
| `backend/app/models/models.py` | Database schema |
| `backend/app/services/storage.py` | Storage provider abstraction |
| `backend/app/services/auth.py` | JWT + password hashing |
| `backend/app/services/rate_limit.py` | IP-based rate limiting |
| `backend/app/services/audit.py` | Audit log writer |
| `backend/seed.py` | Initial data seeder |
| `backend/migrate_41.py` | One-time schema migration (already applied) |
| `change_admin_password.py` | Interactive admin credential updater |
| `frontend/vite.config.js` | Dev server + API proxy |
| `frontend/src/contexts/AuthContext.jsx` | Admin auth state |
| `frontend/src/services/admin.js` | Admin API client + JWT interceptor |
| `frontend/src/router/index.jsx` | All route definitions |
| `.env.example` | Environment variable template |
| `docker-compose.yml` | Local development stack |
| `backend/Dockerfile` | Backend container |
| `ENVIRONMENT_VARIABLES.md` | Full variable reference |
| `RUNNING_GUIDE.md` | All commands to run the project |
| `SELF_HOSTING_GUIDE.md` | Windows self-hosting walkthrough |
| `DOCKER_DEPLOYMENT.md` | Docker-specific deployment |
| `FINAL_DEPLOYMENT_AUDIT.md` | Deployment readiness scores |
