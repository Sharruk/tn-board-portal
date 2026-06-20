# Production Readiness Report
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Supabase Project:** https://fcxvrsgcvmlowehpilvr.supabase.co  
**Build:** `npm run build` — ✅ PASSING (105 modules, 3.24s)

---

## Overall Readiness: 45%

| Layer | Status | Detail |
|---|---|---|
| Frontend code | ✅ Complete | All services, auth, routing migrated to Supabase |
| Production build | ✅ Passing | `vite build` — no errors |
| Vercel SPA routing | ✅ Ready | `frontend/vercel.json` correct |
| Supabase Auth service | ✅ Reachable | `/auth/v1/health` → HTTP 200 |
| Supabase database (PostgREST) | ❌ No tables | HTTP 401 — zero tables in public schema |
| Supabase migrations | ❌ None applied | 001–006 all pending |
| Supabase Storage bucket | ❌ Not created | `/storage/v1/bucket` → `[]` empty |
| Admin user | ❓ Unknown | Cannot verify without tables |

---

## Build Verification ✅

```
> tn-board-frontend@1.0.0 build
> vite build

✓ 105 modules transformed.
dist/index.html                   0.57 kB │ gzip:   0.36 kB
dist/assets/index-*.css           35.40 kB │ gzip:   6.39 kB
dist/assets/index-*.js           529.94 kB │ gzip: 146.88 kB
✓ built in 3.24s
```

No errors. No missing modules. Build output in `frontend/dist/`.

---

## RPC Function Verification ❌

All 5 required functions are missing because **no migrations have been applied**.

| Function | Status | HTTP |
|---|---|---|
| `increment_download_count` | ❌ Not found | 404 |
| `get_admin_stats` | ❌ Not found | 404 |
| `get_search_analytics` | ❌ Not found | 404 |
| `get_content_status` | ❌ Not found | 404 |
| `search_papers` | ❌ Not found | 404 |

---

## Table Verification ❌

All 5 required tables are missing.

| Table | Status | HTTP |
|---|---|---|
| `classes` | ❌ Not found | 404 |
| `subjects` | ❌ Not found | 404 |
| `papers` | ❌ Not found | 404 |
| `audit_logs` | ❌ Not found | 404 |
| `search_queries` | ❌ Not found | 404 |

---

## RLS Policy Verification ❌

Cannot verify — no tables exist to apply policies to.

---

## Storage Verification ❌

| Bucket | Status |
|---|---|
| `papers` | ❌ Does not exist — storage returns empty array |

---

## Authentication Verification ⚠️

| Check | Status |
|---|---|
| Auth service reachable | ✅ HTTP 200 |
| Admin user created | ❓ Cannot verify (requires tables or auth dashboard check) |

---

## Feature Status

### Public Features
| Feature | Status | Reason |
|---|---|---|
| Homepage renders | ✅ | Static HTML loads; stats bar is hardcoded |
| Homepage class cards | ❌ | `getClasses()` fails — no `classes` table |
| Homepage recent papers | ❌ | `getRecentPapers()` fails — no `papers` table |
| Class page | ❌ | No `classes` or `subjects` tables |
| Subject page | ❌ | No `subjects` table |
| Paper detail page | ❌ | No `papers` table |
| Search page | ❌ | `search_papers()` RPC missing |
| Download (increment count) | ❌ | `increment_download_count()` RPC missing |

### Admin Features
| Feature | Status | Reason |
|---|---|---|
| Login page renders | ✅ | Static HTML loads |
| Login (authenticate) | ⚠️ | Auth service alive; may work if admin user was created |
| Dashboard stats | ❌ | `get_admin_stats()` RPC missing |
| Papers list | ❌ | No `papers` table |
| Search analytics | ❌ | `get_search_analytics()` RPC missing |
| Content status | ❌ | `get_content_status()` RPC missing |
| Upload PDF | ❌ | No `papers` bucket in Storage |
| Bulk upload | ❌ | No `papers` bucket in Storage |
| Delete paper | ❌ | No `papers` table or bucket |

---

## Root Cause

> **"4 CLASSES" and "32 SUBJECTS" shown on the homepage are hardcoded static strings in `HomePage.jsx` lines 50–52 — not live database values.** The app appeared to work, but no database connection was actually succeeding.

---

## Remaining Blockers

### Blocker 1 — Database migrations not applied (CRITICAL)

All 6 migrations must be run in the Supabase SQL Editor **in order**:

| Order | Migration | Contents |
|---|---|---|
| 1 | `001_schema.sql` | Creates all 5 tables |
| 2 | `002_seed_data.sql` | Seeds 4 classes + 32 subjects |
| 3 | `003_rls_policies.sql` | Row Level Security on all tables |
| 4 | `004_functions.sql` | 4 RPC functions + GRANT statements |
| 5 | `005_search_analytics.sql` | Index + view + cleanup function |
| 6 | `006_search_rpc.sql` | `search_papers()` cross-table RPC |

Full SQL for each is in **`SUPABASE_DEPLOYMENT_CHECKLIST.md`**.

### Blocker 2 — Storage bucket not created (CRITICAL)

The `papers` bucket must be created in Supabase Dashboard → Storage.  
Steps are in **`SUPABASE_DEPLOYMENT_CHECKLIST.md` Step 5**.

### Blocker 3 — Admin user must be created (required for admin panel)

Create one user in Supabase Dashboard → Authentication → Users.  
Steps are in **`SUPABASE_DEPLOYMENT_CHECKLIST.md` Step 6**.

---

## What Is NOT a Blocker

| Item | Status |
|---|---|
| Frontend code | ✅ Complete — no changes needed |
| `npm run build` | ✅ Passes — no changes needed |
| `frontend/vercel.json` | ✅ Correct — no changes needed |
| Replit secrets | ✅ Both `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` set |
| Vercel environment variables | Needs to be added during Vercel import |

---

## Path to Production

1. Apply all 6 SQL migrations → Supabase SQL Editor (use `SUPABASE_DEPLOYMENT_CHECKLIST.md`)
2. Create `papers` storage bucket → Supabase Storage UI
3. Create admin user → Supabase Authentication UI
4. Deploy to Vercel (steps in `VERCEL_DEPLOYMENT_STEPS.md`)

**Estimated time to complete:** 15–20 minutes of manual Supabase dashboard work.
