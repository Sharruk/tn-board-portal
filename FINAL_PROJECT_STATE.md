# Final Project State
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Supabase Project:** https://fcxvrsgcvmlowehpilvr.supabase.co

---

## Deployment Readiness: 45%

| Layer | Ready | Blocker |
|---|---|---|
| Frontend code | ✅ | — |
| Production build | ✅ | — |
| Supabase credentials | ✅ | — |
| Supabase Auth service | ✅ | — |
| Supabase database tables | ❌ | No migrations applied |
| Supabase seed data | ❌ | No migrations applied |
| Supabase RLS policies | ❌ | No migrations applied |
| Supabase RPC functions | ❌ | No migrations applied |
| Supabase Storage bucket | ❌ | Bucket not created |
| Admin user | ❌ | Not created |

**Readiness rises to 100% after completing `SUPABASE_ACTIVATION_CHECKLIST.md`.**

---

## Current Architecture

```
Browser
  │
  │  HTTPS
  ▼
React SPA (Vite 5 + Tailwind CSS)
  │
  │  Supabase JS Client (anon key, JWT)
  ▼
Supabase
  ├── PostgreSQL (PostgREST REST API)    ← tables, RLS, RPC functions
  ├── Supabase Auth                      ← admin login / session management
  └── Supabase Storage                   ← PDF file hosting (CDN)
```

**No server-side backend.** All data access goes directly from the React frontend to Supabase via the JavaScript client and RLS-protected APIs.

---

## Active Technologies

| Technology | Role | Version / Notes |
|---|---|---|
| React | UI framework | 18.x |
| Vite | Build tool and dev server | 5.x — runs on port 5000 |
| Tailwind CSS | Styling | 3.x |
| React Router | Client-side routing | 6.x |
| Supabase JS | Database / Auth / Storage client | 2.x |
| Supabase PostgreSQL | Primary database | Managed — project ref `fcxvrsgcvmlowehpilvr` |
| Supabase Auth | Authentication | Email + password — anon key in frontend bundle |
| Supabase Storage | PDF file storage | Public bucket `papers` (to be created) |
| PostgREST | REST API layer over PostgreSQL | Managed by Supabase |

---

## Removed Technologies

| Technology | Was used for | Replaced by |
|---|---|---|
| FastAPI (Python) | REST API backend | Supabase PostgREST + RPC functions |
| SQLAlchemy | ORM | Direct Supabase JS client queries |
| Pydantic | Data validation | Supabase JS client + RLS |
| JWT (PyJWT / python-jose) | Authentication tokens | Supabase Auth |
| Uvicorn | ASGI server | No server — SPA only |
| Axios | HTTP client | Supabase JS client |
| In-memory analytics deque | Search tracking | `search_queries` database table |
| `backend/` directory | FastAPI source | Present on disk but entirely unused |
| `Procfile` | Process management | Unused — Replit workflow manages dev server |
| `docker-compose.yml` | Container orchestration | Unused |
| `pyproject.toml` | Python dependencies | Unused |

---

## Migration Files — Verified

All 6 files exist in `supabase/migrations/`. Each is self-contained and safe to re-run.

| File | Size | Status | Objects Created |
|---|---|---|---|
| `001_schema.sql` | 7,869 bytes — 129 lines | ✅ Verified | 5 tables, 12 indexes |
| `002_seed_data.sql` | 4,469 bytes — 82 lines | ✅ Verified | 4 classes, 32 subjects |
| `003_rls_policies.sql` | 6,830 bytes — 193 lines | ✅ Verified | RLS on 5 tables, 13 policies |
| `004_functions.sql` | 9,076 bytes — 265 lines | ✅ Verified | 4 RPC functions, 5 grants |
| `005_search_analytics.sql` | 3,633 bytes — 82 lines | ✅ Verified | 1 index, 1 view, 1 function, 1 grant |
| `006_search_rpc.sql` | 2,805 bytes — 84 lines | ✅ Verified | 1 function (`search_papers`), 2 grants |

---

## Migration Dependency Order

Migrations must be applied in strict order. Each depends on objects from the previous one.

```
001_schema.sql
  └── creates: classes, subjects, papers, audit_logs, search_queries
       │
       ▼
002_seed_data.sql
  └── inserts into: classes, subjects  ← requires 001
       │
       ▼
003_rls_policies.sql
  └── enables RLS on: all 5 tables     ← requires 001
       │
       ▼
004_functions.sql
  └── queries: papers, subjects, classes, search_queries  ← requires 001, 002, 003
       │
       ▼
005_search_analytics.sql
  └── indexes + view on: search_queries  ← requires 001, 003
       │
       ▼
006_search_rpc.sql
  └── joins: papers, subjects, classes  ← requires 001, 002, 003
```

---

## Database Objects — Complete Inventory

### Tables (created by 001)

| Table | Primary Key | Foreign Keys | Purpose |
|---|---|---|---|
| `classes` | `id` (INTEGER) | — | Class 9, 10, 11, 12 |
| `subjects` | `id` (SERIAL) | `class_id → classes.id` | Subjects per class |
| `papers` | `id` (SERIAL) | `subject_id → subjects.id` | Uploaded PDFs |
| `audit_logs` | `id` (SERIAL) | `admin_id → auth.users.id`, `target_paper_id → papers.id` | Admin action history |
| `search_queries` | `id` (SERIAL) | — | Student search history |

### RLS Policies (created by 003)

| Table | Policy | Role | Operation | Rule |
|---|---|---|---|---|
| `classes` | `classes_public_read` | anon, authenticated | SELECT | Always allowed |
| `classes` | `classes_admin_all` | authenticated | ALL | Must be logged in |
| `subjects` | `subjects_public_read` | anon, authenticated | SELECT | Always allowed |
| `subjects` | `subjects_admin_all` | authenticated | ALL | Must be logged in |
| `papers` | `papers_public_read` | anon | SELECT | Only visible papers |
| `papers` | `papers_admin_read` | authenticated | SELECT | All papers |
| `papers` | `papers_admin_insert` | authenticated | INSERT | Must be logged in |
| `papers` | `papers_admin_update` | authenticated | UPDATE | Must be logged in |
| `papers` | `papers_admin_delete` | authenticated | DELETE | Must be logged in |
| `audit_logs` | `audit_logs_admin_read` | authenticated | SELECT | Must be logged in |
| `audit_logs` | `audit_logs_admin_insert` | authenticated | INSERT | Must be logged in |
| `search_queries` | `search_queries_public_insert` | anon, authenticated | INSERT | Always allowed |
| `search_queries` | `search_queries_admin_read` | authenticated | SELECT | Must be logged in |

### Functions (created by 004, 005, 006)

| Function | Called by | Caller role | Returns | Purpose |
|---|---|---|---|---|
| `increment_download_count(paper_id_param)` | `papers.js` | anon | void | Adds 1 to download counter |
| `get_admin_stats()` | `admin.js` | authenticated | 1 row, 7 columns | Dashboard summary numbers |
| `get_search_analytics()` | `admin.js` | authenticated | JSONB | Popular + recent searches |
| `get_content_status()` | `admin.js` | authenticated | JSONB | Exam coverage matrix |
| `prune_old_search_queries(days)` | Manual / SQL Editor | authenticated | INTEGER | Deletes old search rows |
| `search_papers(q, class_id, exam_type, paper_type)` | `search.js` | anon | table (15 cols) | Cross-table search |

### Views (created by 005)

| View | Purpose |
|---|---|
| `search_term_counts` | Top 100 search terms by frequency — convenience view for admin dashboard |

---

## Storage Requirements

| Setting | Required value |
|---|---|
| Bucket name | `papers` |
| Access | Public (students download without logging in) |
| File size limit | 50 MB (52,428,800 bytes) |
| Allowed MIME types | `application/pdf` only |
| Storage RLS — read | `anon` and `authenticated` can SELECT |
| Storage RLS — insert | `authenticated` only |
| Storage RLS — delete | `authenticated` only |

---

## Authentication Requirements

| Requirement | Value |
|---|---|
| Auth provider | Email + password (Supabase built-in) |
| Admin user count | 1 (single admin account) |
| Email confirmation | Must be set to **Auto Confirm** when creating the user |
| Role after login | `authenticated` (standard Supabase role — no custom roles needed) |
| Password minimum | 12 characters recommended — Supabase enforces 6 minimum |
| Site URL (for password reset) | Must match the app's running URL |

---

## Frontend Service Files — What Each Calls

| File | Supabase operations used |
|---|---|
| `src/services/classes.js` | `supabase.from('classes').select(...)` |
| `src/services/papers.js` | `supabase.from('papers').select(...)`, `.insert(...)`, `.update(...)`, `.delete(...)`, `supabase.rpc('increment_download_count', ...)` |
| `src/services/search.js` | `supabase.rpc('search_papers', ...)`, `supabase.from('search_queries').insert(...)` |
| `src/services/admin.js` | `supabase.rpc('get_admin_stats')`, `supabase.rpc('get_search_analytics')`, `supabase.rpc('get_content_status')` |
| `src/contexts/AuthContext.jsx` | `supabase.auth.signInWithPassword(...)`, `supabase.auth.signOut()`, `supabase.auth.getSession()`, `supabase.auth.onAuthStateChange(...)` |

---

## Remaining Blockers

All blockers are Supabase-side manual setup steps. No code changes are required.

| # | Blocker | Resolution | Guide |
|---|---|---|---|
| 1 | No database tables exist | Run migration 001 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 1 |
| 2 | No seed data | Run migration 002 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 2 |
| 3 | No RLS policies | Run migration 003 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 3 |
| 4 | No RPC functions | Run migration 004 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 4 |
| 5 | No analytics objects | Run migration 005 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 5 |
| 6 | No search function | Run migration 006 in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 6 |
| 7 | No `papers` storage bucket | Create bucket in Storage UI | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 7 |
| 8 | No storage RLS policies | Run Block 7 SQL in SQL Editor | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 8 |
| 9 | No admin user | Create user in Authentication UI | `SUPABASE_ACTIVATION_CHECKLIST.md` Step 9 |

---

## What Is Complete and Requires No Changes

| Item | Status |
|---|---|
| All frontend React components | ✅ Complete |
| All 5 service files | ✅ Complete — all Supabase calls implemented |
| Auth context and protected routing | ✅ Complete |
| Supabase JS client configuration | ✅ Complete — reads `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` |
| Replit secrets (both VITE_ variables) | ✅ Set |
| `npm run build` production build | ✅ Passing — 105 modules, 3.24s, no errors |
| All 6 migration SQL files | ✅ Written, verified, self-contained |
| `COPY_PASTE_SQL_ORDER.md` | ✅ All SQL ready to paste |
| `SUPABASE_ACTIVATION_CHECKLIST.md` | ✅ Step-by-step activation guide |
