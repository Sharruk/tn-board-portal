---
name: Supabase migration architecture
description: Full migration from React+FastAPI+JWT to React+Supabase. All service files rewritten. Key decisions and quirks.
---

## What was migrated

- `frontend/src/contexts/AuthContext.jsx` — JWT+localStorage → Supabase Auth sessions (`onAuthStateChange`). Added `isLoading` (undefined = still loading) to prevent premature ProtectedRoute redirect.
- `frontend/src/components/admin/ProtectedRoute.jsx` — now waits for `isLoading` before redirecting.
- `frontend/src/pages/admin/LoginPage.jsx` — username/password → email/password via `supabase.auth.signInWithPassword`.
- `frontend/src/services/admin.js` — Axios adminApi → Supabase queries + RPC. `getAdminStats()` calls `get_admin_stats()` RPC (returns TABLE → use `data[0]`). No default export.
- `frontend/src/services/classes.js`, `subjects.js`, `papers.js`, `search.js` — all rewritten to Supabase.
- `frontend/src/services/api.js` — emptied (was Axios base; kept file to avoid 404s).
- `frontend/hooks/useFetch.js` — error extraction changed from `err.response?.data?.detail` → `err.message`.
- All pages: same `err.response?.data?.detail` → `err.message` fix applied.
- `frontend/vite.config.js` — removed proxy block for `/api` and `/uploads`.
- `frontend/vercel.json` — replaced API rewrites with SPA-only rewrite.

## RPCs required in Supabase

- `get_admin_stats()` → migration 004 — returns TABLE (one row); use `data[0]`.
- `get_search_analytics()` → migration 004 — returns JSONB directly.
- `get_content_status()` → migration 004 — returns JSONB directly.
- `increment_download_count(paper_id_param)` → migration 004 — anon-callable.
- `search_papers(q, p_class_id, p_exam_type, p_paper_type)` → **migration 006** — must be applied manually to Supabase; joins papers+subjects+classes with ILIKE.

## Env vars required

- `VITE_SUPABASE_URL` (secret) — Supabase project URL.
- `VITE_SUPABASE_ANON_KEY` (secret) — Supabase anon/public key (safe to expose to browser).

**Why:** No backend server exists; all DB access is direct from browser via Supabase JS client. Anon key is intentionally public by Supabase design; RLS policies on the DB enforce access control.

## Storage

- Papers uploaded to Supabase Storage bucket `papers` via `supabase.storage.from('papers').upload(...)`.
- Public URL fetched with `getPublicUrl()` and stored in `papers.public_url`.
- On delete, file is removed from storage first, then the DB row.

## Audit logs

- `audit_logs` table: `id, admin_id (UUID), admin_email, action, target_paper_id, target_details (JSONB), ip_address, created_at`.
- `target_details` is JSONB — do NOT `JSON.parse()` it, access directly.
- Timestamp column is `created_at`, not `timestamp`.

## FastAPI backend

- Still running on port 8000 as a separate workflow (`FastAPI Backend`).
- Frontend no longer calls it — all traffic goes to Supabase.
- Can be decommissioned once Supabase is validated end-to-end.
