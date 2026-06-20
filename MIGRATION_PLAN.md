# Migration Plan: React + FastAPI → React + Supabase

**Version:** 1.0  
**Date:** 2026-06-20  
**Based on:** Live codebase inspection of all source files  
**Target:** React 18 + Supabase (Postgres + Auth + Storage) deployed on Vercel  

---

## Phase Overview

| Phase | Scope | Risk | React UI changed? | FastAPI deleted? |
|-------|-------|------|-------------------|-----------------|
| **Phase 1 (this task)** | Supabase schema, RLS, auth setup | Zero — no code touched | No | No |
| **Phase 2** | Replace service layer (6 files + AuthContext) | Low — UI untouched | No UI, services only | No |
| **Phase 3** | Vercel deploy, env vars, smoke test | Low | No | No |
| **Phase 4** | Delete FastAPI after prod verified | Irreversible — do last | No | Yes |

> **Rollback at any phase**: checkout the last checkpoint. Phase 1 and 2 are fully reversible. Phase 4 is not.

---

## Complete File Change Inventory

### Files That Will Be Changed (modified in-place)

| File | Phase | What changes |
|------|-------|-------------|
| `frontend/src/services/api.js` | 2 | Deleted — replaced by Supabase client; file removed |
| `frontend/src/services/admin.js` | 2 | All axios calls rewritten to use `supabase` client |
| `frontend/src/services/classes.js` | 2 | `axios.get('/api/v1/classes')` → `supabase.from('classes').select(...)` |
| `frontend/src/services/subjects.js` | 2 | Rewritten for Supabase queries |
| `frontend/src/services/papers.js` | 2 | Rewritten; download tracking via `supabase.rpc('increment_download_count')` |
| `frontend/src/services/search.js` | 2 | Rewritten; alias expansion moved here from Python; writes to `search_queries` table |
| `frontend/src/contexts/AuthContext.jsx` | 2 | `localStorage` JWT → `supabase.auth.getSession()` / `onAuthStateChange` |
| `frontend/src/pages/admin/LoginPage.jsx` | 2 | `adminLogin()` → `supabase.auth.signInWithPassword()` |
| `frontend/vite.config.js` | 2 | Remove `/api` proxy block (no backend to proxy to) |

### Files That Will Be Created (new)

| File | Phase | Purpose |
|------|-------|---------|
| `supabase/migrations/001_schema.sql` | 1 | Creates all 5 tables with constraints and indexes |
| `supabase/migrations/002_seed_data.sql` | 1 | Seeds 4 classes and 32 subjects (exact match from `seed.py`) |
| `supabase/migrations/003_rls_policies.sql` | 1 | Row Level Security — public read, admin write |
| `supabase/migrations/004_functions.sql` | 1 | RPC functions: `increment_download_count`, `get_content_status` |
| `supabase/migrations/005_search_analytics.sql` | 1 | `search_queries` table + RLS (replaces in-memory `analytics.py`) |
| `supabase/README.md` | 1 | How to apply migrations, create admin user, configure storage bucket |
| `frontend/src/lib/supabase.js` | 2 | Supabase JS client singleton (created once, imported everywhere) |
| `frontend/.env.local.example` | 2 | Template for `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` |

### Files That Will Be Deleted

| File | Phase | Reason |
|------|-------|--------|
| `backend/` (entire directory) | 4 | Replaced by Supabase |
| `Dockerfile` (root) | 4 | Multi-stage build — no longer needed |
| `backend/Dockerfile` | 4 | FastAPI container — no longer needed |
| `docker-compose.yml` | 4 | No backend service to orchestrate |
| `.dockerignore` | 4 | No Docker build |
| `backend/migrate_41.py` | 4 | SQLAlchemy migration — no longer used |
| `backend/seed.py` | 4 | Replaced by `supabase/migrations/002_seed_data.sql` |
| `DOCKER_DEPLOYMENT.md` | 4 | No longer applicable |
| `SELF_HOSTING_GUIDE.md` | 4 | Replaced by simpler Vercel guide |
| `RUNNING_GUIDE.md` | 4 | Rewritten for Supabase stack |

### Files Requiring Zero Changes (confirmed)

These files are **unaffected** by the migration. All UI work is preserved:

**All 12 page components:** `HomePage.jsx`, `ClassPage.jsx`, `SubjectPage.jsx`, `PaperListPage.jsx`, `PaperDetailPage.jsx`, `SearchPage.jsx`, `NotFoundPage.jsx`, `DashboardPage.jsx`, `PapersPage.jsx`, `BulkUploadTab.jsx`, `LoginPage.jsx` (minor change only), `ContentStatusPage.jsx`

**All 8 shared components:** `ClassCard.jsx`, `PaperCard.jsx`, `Navbar.jsx`, `Footer.jsx`, `Breadcrumb.jsx`, `LoadingSpinner.jsx`, `ErrorMessage.jsx`, `SearchBar.jsx`

**Layouts and routing:** `MainLayout.jsx`, `AdminLayout.jsx`, `ProtectedRoute.jsx`, `router/index.jsx`

**Hooks and styling:** `hooks/useFetch.js`, `tailwind.config.js`, `postcss.config.js`

---

## Step-by-Step Migration

### Phase 1 — Foundation (this task, zero risk)

**Goal:** Create all Supabase assets. Touch zero application code.

**Step 1.1 — Create Supabase project**
1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose region closest to your users (e.g. `ap-south-1` Mumbai for Indian students)
3. Set a strong database password and save it

**Step 1.2 — Apply SQL migrations**  
In Supabase Dashboard → SQL Editor, run each file in order:
1. `supabase/migrations/001_schema.sql`
2. `supabase/migrations/002_seed_data.sql`
3. `supabase/migrations/003_rls_policies.sql`
4. `supabase/migrations/004_functions.sql`
5. `supabase/migrations/005_search_analytics.sql`

**Step 1.3 — Create admin user in Supabase Auth**  
In Supabase Dashboard → Authentication → Users → Add User:
- Email: `admin@tnboard.local` (or your real email)
- Password: minimum 12 characters, mixed case + numbers + symbols
- Check "Auto-confirm user"

**Step 1.4 — Create Storage bucket**  
In Supabase Dashboard → Storage → New Bucket:
- Name: `papers`
- Toggle: Public bucket ON
- File size limit: 52428800 (50 MB)
- Allowed MIME types: `application/pdf`

**Step 1.5 — Collect credentials**  
From Supabase Dashboard → Settings → API:
- `Project URL` → this becomes `VITE_SUPABASE_URL`
- `anon` key → this becomes `VITE_SUPABASE_ANON_KEY`  
- `service_role` key → save securely for admin scripts (never used in frontend)

---

### Phase 2 — Service Layer Replacement

**Goal:** Replace 6 service files + AuthContext. No page files change.

**Step 2.1** — Create `frontend/src/lib/supabase.js`  
Single import point for the Supabase client.

**Step 2.2** — Rewrite `frontend/src/services/classes.js`  
`axios.get('/api/v1/classes')` → `supabase.from('classes').select('*, subjects(count)')`

**Step 2.3** — Rewrite `frontend/src/services/subjects.js`  
Fetches subjects by class_id. Paper count via join.

**Step 2.4** — Rewrite `frontend/src/services/papers.js`  
Public queries filter `is_visible = true` (enforced by RLS anyway).  
Download tracking calls `supabase.rpc('increment_download_count', { paper_id_param: id })`.

**Step 2.5** — Rewrite `frontend/src/services/search.js`  
Alias dict (20 entries) moved from Python to JS.  
Search uses `supabase.from('papers').select(...).ilike('title', term)` with OR conditions.  
Writes term + result_count to `search_queries` table after each search.

**Step 2.6** — Rewrite `frontend/src/services/admin.js`  
All admin CRUD calls use Supabase JS client.  
File upload uses `supabase.storage.from('papers').upload(filename, file)`.  
Each mutating operation inserts a row into `audit_logs`.

**Step 2.7** — Rewrite `frontend/src/contexts/AuthContext.jsx`  
`supabase.auth.getSession()` on mount.  
`supabase.auth.onAuthStateChange()` for reactive updates.  
`supabase.auth.signOut()` for logout.

**Step 2.8** — Update `frontend/src/pages/admin/LoginPage.jsx`  
One function call change: `supabase.auth.signInWithPassword({ email, password })`.

**Step 2.9** — Update `frontend/vite.config.js`  
Remove the `server.proxy` block. Add Supabase env var validation.

---

### Phase 3 — Vercel Deployment

**Goal:** Get the app live on Vercel.

**Step 3.1** — Push code to GitHub  
**Step 3.2** — Import repository in Vercel  
**Step 3.3** — Set environment variables in Vercel:
- `VITE_SUPABASE_URL` = your Supabase project URL
- `VITE_SUPABASE_ANON_KEY` = your Supabase anon key
**Step 3.4** — Deploy and run smoke tests  
**Step 3.5** — Verify all routes, uploads, and admin functions  

---

### Phase 4 — Cleanup (after production is verified)

**Goal:** Delete FastAPI and all backend infrastructure.

**Step 4.1** — Confirm Vercel deployment is fully functional (minimum 24 hours)  
**Step 4.2** — Delete `backend/` directory  
**Step 4.3** — Delete Docker files, backend-only docs  
**Step 4.4** — Update `replit.md`, `README.md`  
**Step 4.5** — Remove FastAPI workflow from `.replit`  

> Phase 4 is a git commit with a clear message. If anything breaks after this, restore from the last checkpoint before the commit.

---

## Data Preservation

### Current state of data
The current Replit PostgreSQL database contains:
- **4 classes** (Class 9–12) — seeded by `seed.py`
- **32 subjects** — seeded by `seed.py`
- **0 papers** — none have been uploaded to production yet (confirmed: no production deployment exists)
- **1 admin** — `admin` / `admin123` (dev credentials, must not be reused)

### Migration approach
Because there are no papers to migrate, data preservation is simple:

1. Classes and subjects are **re-seeded** via `supabase/migrations/002_seed_data.sql`
2. Admin credentials are **recreated** in Supabase Auth (new password required)
3. No PDF files need moving — no files were uploaded to production storage

### If papers existed (for future reference)
If papers had been uploaded to production Supabase Storage, the migration would:
1. Export `papers` table to CSV from old DB
2. Import CSV into Supabase via `COPY` in SQL Editor
3. Verify `public_url` values still resolve (they would, since Supabase Storage URLs are permanent)

---

## Rollback Procedure

### Phase 1 rollback (before any code changes)
The Supabase migrations are **additive** and exist on an **external service**, not in the codebase.  
Rollback = do nothing. The Replit app is unchanged.  
If the Supabase project needs to be cleaned up: Dashboard → Settings → Delete Project.

### Phase 2 rollback
Every modified file is tracked in git. Rollback procedure:
1. In Replit → History → find the checkpoint before Phase 2 began
2. Click Restore
3. The FastAPI backend is still running — the app is immediately functional again

### Phase 3 rollback
Vercel keeps every deployment. Rollback:
1. Vercel Dashboard → your project → Deployments
2. Find the previous deployment → Redeploy
3. Takes under 60 seconds

### Phase 4 rollback (critical — only possible via git)
Phase 4 deletes files. Recovery:
1. Replit → History → find checkpoint before Phase 4 commit
2. Click Restore
3. Restart the FastAPI workflow
4. App is fully restored

> Always run `git log` and confirm the checkpoint exists before executing Phase 4.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Supabase free tier hits limits | Low | Medium | 500 MB DB / 1 GB Storage is sufficient for years of question papers |
| RLS policy blocks a valid query | Low | High | All policies are tested in SQL Editor before Phase 2 begins |
| `useFetch` hook expects specific response shape | Low | Low | Hook is generic — works with any object/array return |
| `ProtectedRoute` breaks with new auth | Low | Medium | AuthContext interface is unchanged — same `user`, `logout` exports |
| Supabase anon key exposed in frontend bundle | Intentional | None | Anon key is designed to be public — RLS enforces all restrictions |
| Admin forgets Supabase Auth password | Low | Medium | Supabase Dashboard → Auth → Users → Reset password |

---

## Architecture Comparison: Before and After

| Concern | Before (FastAPI) | After (Supabase) |
|---------|-----------------|-----------------|
| Auth token | JWT in localStorage (PyJWT) | Supabase session (httpOnly cookie optional) |
| Auth enforcement | FastAPI `Depends(get_current_admin)` | Supabase RLS `auth.uid() IS NOT NULL` |
| Rate limiting | In-memory dict (resets on restart) | Supabase Auth built-in (GoTrue) |
| File upload | FastAPI multipart → Supabase Storage | Browser → Supabase Storage direct |
| Search analytics | In-memory deque (resets on restart) | `search_queries` Postgres table (durable) |
| Audit logs | Server-enforced (FastAPI middleware) | Client-written (React inserts to `audit_logs`) |
| Download count | `POST /papers/{id}/download` (REST) | `supabase.rpc('increment_download_count')` |
| Content status | Server-computed join | Client-computed from Supabase data |
