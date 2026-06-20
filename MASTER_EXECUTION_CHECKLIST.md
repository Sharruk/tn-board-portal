# Master Execution Checklist
## TN State Board Learning Platform — Migration to React + Supabase + Vercel

**Execute phases in order. Do not start Phase N+1 until Phase N is fully verified.**

---

## Phase 1 — Supabase Setup

### 1.1 Database
- [ ] Create a new Supabase project at supabase.com
- [ ] Open SQL Editor → run `supabase/migrations/001_schema.sql`
- [ ] Run `supabase/migrations/002_seed_data.sql`
- [ ] Verify: `SELECT COUNT(*) FROM classes` = 4, `FROM subjects` = 32
- [ ] Run `supabase/migrations/003_rls_policies.sql`
- [ ] Verify: 12 RLS policies exist across 5 tables
- [ ] Run `supabase/migrations/004_functions.sql`
- [ ] Verify: `SELECT * FROM get_admin_stats()` returns a row without error
- [ ] Run `supabase/migrations/005_search_analytics.sql`
- [ ] Verify: `idx_search_queries_normalised_term` index exists

### 1.2 Storage
- [ ] Storage → New Bucket → Name: `papers`, Public: ON, Size limit: 52428800, MIME: `application/pdf`
- [ ] Apply `papers_bucket_public_read` policy (from `supabase/README.md`)
- [ ] Apply `papers_bucket_admin_insert` policy
- [ ] Apply `papers_bucket_admin_delete` policy

### 1.3 Auth
- [ ] Authentication → Users → Add user → enter admin email + strong password → Auto-confirm: ON
- [ ] Copy admin user UID (for reference if needed)
- [ ] Test login in Supabase Auth API explorer (optional sanity check)

### 1.4 Collect Credentials
- [ ] Copy **Project URL** from Settings → API → Project URL
- [ ] Copy **anon key** from Settings → API → Project API keys → `anon`
- [ ] Store both values securely (needed for Step 3)

---

## Phase 2 — Migrate Existing Data (if applicable)

> Skip this phase if no papers have been uploaded yet.

- [ ] Export paper rows from current DB: `SELECT * FROM papers ORDER BY id`
- [ ] Identify papers with local storage URLs: `WHERE public_url LIKE '/uploads/%'`
- [ ] For Supabase-stored papers: import rows to new Supabase DB via SQL Editor
- [ ] Reset sequence: `SELECT setval('papers_id_seq', (SELECT MAX(id) FROM papers))`
- [ ] Verify paper count matches original
- [ ] Plan re-upload of any locally-stored PDFs via new admin UI after migration

---

## Phase 3 — Frontend Code Migration

### 3.1 Install Supabase
- [ ] `cd frontend && npm install @supabase/supabase-js`

### 3.2 Add Supabase client
- [ ] Create `frontend/src/lib/supabase.js` with `createClient()`
- [ ] Create `frontend/.env.local` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`

### 3.3 Replace services
- [ ] Replace `frontend/src/services/classes.js` with Supabase queries
- [ ] Replace `frontend/src/services/subjects.js` with Supabase queries
- [ ] Replace `frontend/src/services/papers.js` with Supabase queries + hardcoded exam types
- [ ] Replace `frontend/src/services/search.js` with Supabase query + search_queries insert
- [ ] Replace `frontend/src/services/admin.js` with Supabase calls
- [ ] Delete `frontend/src/services/api.js` (Axios base client)

### 3.4 Replace auth
- [ ] Replace `frontend/src/contexts/AuthContext.jsx` with Supabase session management
- [ ] Update `frontend/src/pages/admin/LoginPage.jsx` → use `signInWithPassword`
- [ ] Update `frontend/src/components/admin/ProtectedRoute.jsx` → check `session` not `token`

### 3.5 Update admin pages
- [ ] Update `DashboardPage.jsx` → call `getAdminStats()` (renamed from `getStats`)
- [ ] Update `PapersPage.jsx` → upload via Supabase Storage directly
- [ ] Update `BulkUploadTab.jsx` → upload via Supabase Storage directly

### 3.6 Config cleanup
- [ ] Update `frontend/vite.config.js` → remove proxy block
- [ ] Replace `frontend/vercel.json` → single SPA rewrite only
- [ ] Optionally remove `axios`: `npm uninstall axios`

---

## Phase 4 — Local Testing

- [ ] `cd frontend && npm run dev`
- [ ] Homepage loads: class cards show with correct subject counts
- [ ] Class page loads: subjects with paper counts
- [ ] Subject page loads: papers grouped by exam type
- [ ] Search works: results appear, check `search_queries` table in Supabase Dashboard
- [ ] Paper detail loads: PDF viewer, YouTube embed if present
- [ ] Download button: increments `download_count` in DB (check in Supabase Dashboard)
- [ ] Admin login: `supabase.auth.signInWithPassword()` → redirects to dashboard
- [ ] Admin dashboard: stats load (4 classes, 32 subjects, total papers)
- [ ] Admin papers list: all papers visible (including hidden ones)
- [ ] Upload paper: file appears in Supabase Storage, row created in `papers` table
- [ ] Edit paper: toggle `is_visible`, change YouTube URL
- [ ] Delete paper: row removed from DB, file removed from Storage
- [ ] Content status page loads: coverage matrix visible
- [ ] Audit logs: upload/edit/delete actions logged in `audit_logs` table
- [ ] Logout: session cleared, redirected to login

---

## Phase 5 — Vercel Deployment

- [ ] Push migrated frontend to GitHub repository
- [ ] Import repo in Vercel Dashboard → New Project
- [ ] Set Root Directory: `frontend`
- [ ] Set Framework Preset: Vite
- [ ] Add env var: `VITE_SUPABASE_URL`
- [ ] Add env var: `VITE_SUPABASE_ANON_KEY`
- [ ] Deploy
- [ ] Copy Vercel URL (e.g., `https://your-app.vercel.app`)
- [ ] Set Supabase → Authentication → Site URL = `https://your-app.vercel.app`
- [ ] Set Supabase → Authentication → Redirect URLs = `https://your-app.vercel.app/**`

---

## Phase 6 — Production Verification

- [ ] Homepage loads at Vercel URL
- [ ] Navigating to `/search` and refreshing does NOT 404
- [ ] Admin login works with Supabase Auth credentials
- [ ] Upload a test PDF → verify in Supabase Storage bucket
- [ ] Download test PDF → CDN URL resolves, `download_count` increments
- [ ] Delete test PDF → removed from Storage and DB

---

## Phase 7 — Cleanup (After Verification)

- [ ] Drop `admins` table: `DROP TABLE IF EXISTS admins CASCADE;`
- [ ] Delete `backend/` directory from repository
- [ ] Delete root `Dockerfile`
- [ ] Delete `docker-compose.yml`
- [ ] Delete `Procfile`
- [ ] Delete `change_admin_password.py`
- [ ] Delete `backend/migrate_41.py`
- [ ] Update `README.md` to reflect new architecture
- [ ] Remove `RUNNING_GUIDE.md` or update for Vercel-only workflow
- [ ] Commit and push → Vercel auto-redeploys

---

## Rollback Plan

If anything fails during Phase 3–4, the original FastAPI backend is still intact and running. To roll back:
1. Revert the service files to their Axios versions
2. Revert `AuthContext.jsx` and auth-related files
3. Restart the FastAPI Backend workflow in Replit

No database data is lost during migration — the Supabase DB is a separate system.

---

## Time Estimate

| Phase | Estimated Time |
|---|---|
| Phase 1 — Supabase Setup | 30–60 minutes |
| Phase 2 — Data Migration | 15 minutes (if papers exist) |
| Phase 3 — Code Migration | 3–5 hours |
| Phase 4 — Local Testing | 1–2 hours |
| Phase 5 — Vercel Deploy | 15–30 minutes |
| Phase 6 — Verification | 30 minutes |
| Phase 7 — Cleanup | 15 minutes |
| **Total** | **~6–10 hours** |
