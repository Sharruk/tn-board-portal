# Final Deployment Audit — TN State Board Learning Platform

Audit date: 2026-06-20 | Inspector: automated codebase analysis

---

## Scores

| Category          | Score  | Notes                                              |
|-------------------|--------|----------------------------------------------------|
| Security          | 82/100 | JWT solid; rate limiter in-memory only; seed password printed |
| Deployment        | 76/100 | Docker ready; no CI/CD; local Dockerfile conflicts |
| Code Quality      | 88/100 | Clean separation; minor: hardcoded email in migrate_41.py |
| Architecture      | 90/100 | Proper layering; storage abstraction excellent      |
| Documentation     | 95/100 | Comprehensive after this audit                     |
| Maintainability   | 85/100 | Well structured; pyproject.toml has legacy deps    |

**Overall: 86/100**

---

## Security

### ✅ Passed

- **JWT implementation** — HS256, signed with env-configured secret, expiry enforced
- **Password hashing** — Werkzeug `generate_password_hash` (scrypt by default)
- **Account lockout** — 5 failed attempts → 15 minute account lock (DB-persisted, survives restart)
- **IP rate limiting** — 5 failed attempts per IP within 15 minutes → 15 minute block
- **Audit logging** — All login attempts, uploads, edits, deletes recorded in `audit_logs`
- **CORS enforcement** — `*` raises `RuntimeError` in `ENVIRONMENT=production`
- **JWT_SECRET_KEY enforcement** — insecure default raises `RuntimeError` in production
- **X-Forwarded-For** — client IP extracted from proxy headers correctly
- **Duplicate upload prevention** — 409 returned for same title/subject/year/exam_type
- **File type validation** — only `.pdf` accepted
- **File size limit** — configurable via `MAX_FILE_SIZE_MB` (default 50 MB)
- **No secrets in source** — no API keys, passwords, or tokens hardcoded in active code

### ⚠️ Warnings

- **In-memory rate limiter** — `services/rate_limit.py` stores IP state in a Python dict. If the backend runs with multiple Uvicorn workers (`--workers N`), each worker has an independent store. A locked IP can authenticate through a different worker. Fix: use Redis for shared state.
- **Seed password visible** — `backend/seed.py` prints the default password (`admin123`) to stdout on first run. Acceptable for development, but production deployments must run `change_admin_password.py` before going live.
- **migrate_41.py contains an email address** — a specific email (`hungrylearner786@gmail.com`) is hardcoded. This is a one-time migration file but ideally should prompt interactively or be removed after migration.
- **JWT tokens in localStorage** — the frontend stores the admin JWT in `localStorage`. This is the standard approach for SPAs but is vulnerable to XSS. For higher security, use HttpOnly cookies.

---

## Deployment Readiness

### Railway (Backend)

| Check                         | Status | Notes                                  |
|-------------------------------|--------|----------------------------------------|
| Dockerfile present            | ✅     | `backend/Dockerfile` — Python 3.12-slim |
| Port configured               | ✅     | `EXPOSE 8000`, `--port 8000`           |
| DATABASE_URL via env          | ✅     | Read from environment, not hardcoded    |
| Production mode available     | ✅     | Set `ENVIRONMENT=production`           |
| Health check endpoint         | ✅     | `GET /health` returns `{"status":"healthy"}` |
| Static files                  | ✅     | Serves `frontend/dist/` when built     |

**Railway deploy steps:**
1. Connect GitHub repo to Railway
2. Set root directory to `backend/`
3. Configure environment variables (see `ENVIRONMENT_VARIABLES.md`)
4. Deploy — Railway auto-detects `Dockerfile`
5. Run seed after first deploy: `railway run python seed.py`

### Vercel (Frontend)

| Check                         | Status | Notes                                     |
|-------------------------------|--------|-------------------------------------------|
| React/Vite project            | ✅     | Standard Vite setup                       |
| Build command                 | ✅     | `npm run build` → `dist/`                 |
| Output directory              | ✅     | `dist`                                    |
| API proxy                     | ⚠️     | Vite proxy only works in dev; prod needs `vercel.json` rewrites |
| SPA routing                   | ⚠️     | Needs `vercel.json` to catch all routes   |

**Vercel deploy steps:**
1. Import repo on vercel.com
2. Set **Root Directory** to `frontend`
3. Framework: Vite (auto-detected)
4. Build command: `npm run build`
5. Output: `dist`
6. Add `vercel.json` (see below)
7. Set `VITE_API_BASE_URL=https://your-railway-backend.up.railway.app` in Vercel env vars

**Required `frontend/vercel.json`:**
```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://your-backend.up.railway.app/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### Supabase Integration

| Check                                | Status | Notes                                  |
|--------------------------------------|--------|----------------------------------------|
| Client library installed             | ✅     | `supabase==2.31.0` in requirements     |
| Provider implemented                 | ✅     | `SupabaseStorageProvider` in storage.py |
| Bucket must be Public                | ✅     | Documented in storage.py               |
| Service role key required (not anon) | ✅     | Validated in `SupabaseStorageProvider.__init__` |
| Env vars validated at startup        | ✅     | `RuntimeError` if missing              |

### CORS

| Check                          | Status | Notes                                      |
|--------------------------------|--------|--------------------------------------------|
| CORS middleware configured     | ✅     | `CORSMiddleware` in `main.py`             |
| `*` blocked in production      | ✅     | `RuntimeError` raised                     |
| Credentials mode               | ✅     | `allow_credentials=True`                  |
| All methods/headers allowed    | ✅     | `allow_methods=["*"]`, `allow_headers=["*"]` |

### API Routing

| Check                        | Status | Notes                                       |
|------------------------------|--------|---------------------------------------------|
| All routers mounted          | ✅     | classes, subjects, papers, auth, admin      |
| API prefix                   | ✅     | `/api/v1` prefix on all routes              |
| 404 for unknown API paths    | ✅     | FastAPI default                             |
| Download count tracking      | ✅     | `POST /papers/{id}/download`                |
| Search with alias expansion  | ✅     | "maths" → "mathematics" etc.               |

### SPA Routing

| Check                        | Status | Notes                                         |
|------------------------------|--------|-----------------------------------------------|
| Dev: Vite proxy              | ✅     | `/api/*` and `/uploads/*` proxied to :8000    |
| Prod: FastAPI catch-all      | ✅     | `/{full_path:path}` returns `index.html`      |
| Assets served                | ✅     | `/assets/` mounted from `frontend/dist/assets/` |

### Build Process

| Check                          | Status | Notes                                    |
|--------------------------------|--------|------------------------------------------|
| `npm run build` works          | ✅     | Vite produces `frontend/dist/`           |
| Production env detection       | ✅     | `IS_PRODUCTION` flag in `config.py`      |
| Docs disabled in production    | ✅     | `/docs`, `/redoc` return 404             |

### GitHub Readiness

| Check                      | Status | Notes                              |
|----------------------------|--------|------------------------------------|
| `.gitignore` present       | ✅     | Covers `.env`, `__pycache__`, etc. |
| No `.env` committed        | ✅     | `.env` in `.gitignore`             |
| No hardcoded secrets       | ✅     | Config reads from environment      |
| Legacy files removed       | ✅     | No `app.py`, `templates/`, `static/` |

---

## Issues Found and Status

| Issue | Severity | Fixed? |
|-------|----------|--------|
| `pyproject.toml` lists 7 unused Flask-era packages | Medium | ✅ Fixed in this audit |
| Root `Dockerfile` describes legacy Flask/gunicorn setup | Medium | ✅ Fixed in this audit |
| `backend/requirements.txt` has PyJWT/pydantic version conflict | High | ✅ Fixed in this audit |
| `.gitignore` missing `frontend/dist/`, `frontend/node_modules/`, `.pythonlibs/` | Low | ✅ Fixed in this audit |
| In-memory rate limiter doesn't work across multiple workers | Medium | ⚠️ Documented — requires Redis |
| `migrate_41.py` contains a hardcoded personal email | Low | ⚠️ One-time file — document only |
| No `docker-compose.yml` | Medium | ✅ Created in this audit |
| No `.dockerignore` | Low | ✅ Created in this audit |
| No `frontend/vercel.json` for Vercel deployment | Medium | ⚠️ Documented — add before deploying |
