# Current Migration Status
## TN State Board Learning Platform — React + FastAPI → React + Supabase

**Audit Date:** 2026-06-20  
**Auditor:** Replit Agent (read-only scan)

---

## Deployment Readiness: 88%

| Layer | Status |
|---|---|
| Frontend code migration | ✅ 100% complete |
| Build pipeline | ✅ Working |
| Vercel SPA routing | ✅ Configured |
| Supabase DB schema / migrations | ⚠️ SQL files exist, must confirm applied |
| Runtime credentials (Replit Secrets) | ❌ Not set |
| Backend removal / cleanup | ⚠️ Backend folder still present (unused) |
| Root-level vercel.json | ⚠️ Missing (only frontend/vercel.json exists) |

---

## Completed Work

### Frontend — 100% migrated

Every file in `frontend/src/` now talks exclusively to Supabase. Zero Axios calls. Zero FastAPI references.

**`frontend/src/lib/supabase.js`** — EXISTS  
- Reads `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from `import.meta.env`  
- Falls back to placeholder strings if missing (app loads but all queries fail)

**`frontend/src/services/` — all 5 files fully migrated**

| File | Was using | Now using | Status |
|---|---|---|---|
| `api.js` | Axios / FastAPI base client | `export {}` (empty, gutted) | ✅ Done |
| `papers.js` | FastAPI `/papers/*` | `supabase.from('papers')` | ✅ Done |
| `classes.js` | FastAPI `/classes/*` | `supabase.from('classes')` | ✅ Done |
| `subjects.js` | FastAPI `/subjects/*` | `supabase.from('subjects')` | ✅ Done |
| `search.js` | FastAPI `/search` | `supabase.rpc('search_papers')` | ✅ Done |
| `admin.js` | FastAPI `/admin/*` | `supabase.from(...)` + `supabase.storage` | ✅ Done |

**`frontend/src/contexts/AuthContext.jsx`** — Uses `supabase.auth.getSession()` and `supabase.auth.onAuthStateChange()`. No JWT, no localStorage token management.

**`frontend/src/pages/admin/LoginPage.jsx`** — Uses `supabase.auth.signInWithPassword()`. No FastAPI `/auth/login` call.

**Build** — `npm run build` completes cleanly in 3.73s. No errors. Output: `frontend/dist/`.

**`frontend/vercel.json`** — Exists with correct SPA rewrite:
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

**Supabase DB migrations** — SQL files exist in `supabase/migrations/` (001–006), covering schema, seed data, RLS policies, functions, and search RPC.

---

## Remaining Work

### 1. ❌ Runtime credentials — NOT set (hard blocker)

The app loads but every data request fails silently because `supabase.js` falls back to `'placeholder-key'`.

| Secret | Used in | Why required |
|---|---|---|
| `VITE_SUPABASE_URL` | `frontend/src/lib/supabase.js` line 3 | Without this, all API calls go to `https://placeholder.supabase.co` — a non-existent host. Every query returns a network error. |
| `VITE_SUPABASE_ANON_KEY` | `frontend/src/lib/supabase.js` line 4 | Without this, every request is rejected with HTTP 401 by Supabase. No data can be read or written. |

Known value from your project context:
- `VITE_SUPABASE_URL` = `https://fcxvrsgcvmlowehpilvr.supabase.co`
- `VITE_SUPABASE_ANON_KEY` = **unknown — needs to be provided**

> **Note:** The anon key is safe to put in Replit Secrets as `VITE_SUPABASE_ANON_KEY`. It is a public-facing key. All access control is enforced by Supabase RLS policies, not by keeping this key secret.

---

### 2. ⚠️ Supabase migrations — confirm applied

`supabase/migrations/` contains 6 SQL files that must be run against your Supabase project **in order** before the app can function:

| File | What it does |
|---|---|
| `001_schema.sql` | Creates all 5 tables |
| `002_seed_data.sql` | Seeds 4 classes + 32 subjects |
| `003_rls_policies.sql` | Enables Row Level Security on all tables |
| `004_functions.sql` | Creates RPC functions (`increment_download_count`, `get_admin_stats`, etc.) |
| `005_search_analytics.sql` | Adds analytics index, view, and cleanup function |
| `006_search_rpc.sql` | Creates `search_papers()` cross-table full-text search function |

> If these have already been applied to your Supabase project, this item is complete.

---

### 3. ⚠️ Backend folder — present but completely unused

`backend/` contains the full FastAPI application (models, routes, services, seed scripts). **None of these files are imported or called by the frontend.** The backend is dead code.

Recommended action: Delete the `backend/` directory. It adds confusion but causes no functional harm while it sits there.

---

### 4. ⚠️ Root-level `vercel.json` — missing

`frontend/vercel.json` exists with the SPA rewrite rule. However, if deploying from the **repo root** on Vercel (rather than setting the root directory to `frontend/`), a root-level `vercel.json` is needed to:
- Point the build to `frontend/`
- Set environment variables for the build

This only matters for Vercel deployment, not for Replit dev.

---

### 5. ⚠️ Stale files (not harmful, but cluttered)

| File | Issue |
|---|---|
| `Procfile` | Says `web: gunicorn app:app` — references a Flask app that no longer exists |
| `pyproject.toml` | Lists Flask/FastAPI Python dependencies — no longer needed |
| `docker-compose.yml` / `Dockerfile` | Containers for the old FastAPI stack — orphaned |
| `archive/` | 10 old report `.txt` files — safe to delete |
| `*.md` planning docs (20+) | Migration planning docs — no longer actionable |

---

## Files Migrated (Frontend — all done)

```
frontend/src/lib/supabase.js          ✅ Supabase client
frontend/src/contexts/AuthContext.jsx  ✅ Supabase Auth
frontend/src/services/api.js          ✅ Gutted (empty)
frontend/src/services/papers.js       ✅ Supabase
frontend/src/services/classes.js      ✅ Supabase
frontend/src/services/subjects.js     ✅ Supabase
frontend/src/services/search.js       ✅ Supabase RPC
frontend/src/services/admin.js        ✅ Supabase + Supabase Storage
frontend/src/pages/admin/LoginPage.jsx ✅ Supabase Auth
frontend/src/pages/admin/DashboardPage.jsx ✅ (via admin.js)
frontend/src/pages/admin/PapersPage.jsx    ✅ (via admin.js + classes.js)
frontend/src/pages/admin/BulkUploadTab.jsx ✅ (via admin.js + classes.js)
frontend/src/pages/admin/ContentStatusPage.jsx ✅ (via admin.js)
frontend/src/router/index.jsx         ✅ No backend references
frontend/vercel.json                  ✅ SPA routing configured
```

## Files NOT Migrated (Backend — unused, pending deletion)

```
backend/app/main.py              ❌ FastAPI entry point — unused
backend/app/api/*.py             ❌ FastAPI routes — unused
backend/app/models/models.py     ❌ SQLAlchemy models — unused
backend/app/services/*.py        ❌ JWT, storage, rate-limit — unused
backend/requirements.txt         ❌ Old Python deps — unused
backend/seed.py                  ❌ Superseded by 002_seed_data.sql
Procfile                         ⚠️ Wrong (Flask) — stale
pyproject.toml                   ⚠️ Wrong (Flask/FastAPI) — stale
docker-compose.yml / Dockerfile  ⚠️ Old stack — stale
```

---

## What Happens After Approval

Proposed next steps (awaiting your go-ahead):

1. **Set `VITE_SUPABASE_ANON_KEY` secret** — you provide the anon key, I set it in Replit Secrets.  
   `VITE_SUPABASE_URL` is already known (`https://fcxvrsgcvmlowehpilvr.supabase.co`) and can be set immediately.

2. **Confirm migrations applied** — if not, I can provide the exact SQL to run in Supabase Dashboard.

3. **Restart dev server** — Vite will pick up the new env vars and the app will function end-to-end.

4. **Optional cleanup** — delete `backend/`, stale docs, `Procfile`, orphaned Docker files.

5. **Optional: add root `vercel.json`** — if you plan to deploy to Vercel from repo root.

---

**Awaiting your approval before making any changes.**
