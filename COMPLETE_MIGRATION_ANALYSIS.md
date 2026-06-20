# Complete Migration Analysis
## TN State Board Learning Platform — FastAPI → React + Supabase + Vercel

**Date:** 2026-06-20  
**Status:** Analysis only — no code modified

---

## 1. Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                           │
│              React 18 + Vite 5 + TailwindCSS             │
│                                                           │
│   Public Portal          │        Admin Dashboard         │
│   (anonymous users)      │        (JWT-authenticated)     │
└────────────┬─────────────┴──────────────┬────────────────┘
             │ Axios HTTP                  │ Axios + Bearer token
             │ /api/v1/*                   │ /api/v1/admin/*
             ▼                             ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI (Python 3.11)                  │
│               Uvicorn — port 8000 (dev)                   │
│               Uvicorn — port 5000 (prod, serves SPA)      │
│                                                           │
│  Routers:                                                 │
│    /classes      /subjects     /papers                    │
│    /auth         /admin        /search                    │
│    /exam-types                                            │
│                                                           │
│  Services:                                                │
│    auth.py       storage.py    rate_limit.py              │
│    audit.py      analytics.py                             │
└────────────┬──────────────────────────┬──────────────────┘
             │ SQLAlchemy               │ supabase-py
             ▼                          ▼
┌─────────────────────┐    ┌──────────────────────────────┐
│  PostgreSQL DB       │    │     Supabase Storage          │
│  (Replit-managed)    │    │     bucket: papers            │
│                      │    │     (PDF CDN URLs)            │
│  classes             │    └──────────────────────────────┘
│  subjects            │
│  papers              │    ┌──────────────────────────────┐
│  admins              │    │  In-Memory (per-process)      │
│  audit_logs          │    │  analytics.py — deque/dict    │
│                      │    │  rate_limit.py — dict         │
└─────────────────────┘    └──────────────────────────────┘
```

---

## 2. Target Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                           │
│              React 18 + Vite 5 + TailwindCSS             │
│                                                           │
│   Public Portal          │        Admin Dashboard         │
│   (anonymous users)      │        (Supabase Auth session) │
└────────────┬─────────────┴──────────────┬────────────────┘
             │ @supabase/supabase-js        │ @supabase/supabase-js
             │ (anon key, RLS enforced)     │ (authenticated session)
             ▼                             ▼
┌─────────────────────────────────────────────────────────┐
│                      Supabase                            │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL (Supabase-managed)                   │    │
│  │                                                   │    │
│  │  classes          subjects          papers         │    │
│  │  audit_logs       search_queries                  │    │
│  │  (admins table REMOVED → Supabase Auth)           │    │
│  │                                                   │    │
│  │  RLS policies enforce all access rules            │    │
│  │  RPC functions: get_admin_stats()                 │    │
│  │                 get_search_analytics()            │    │
│  │                 get_content_status()              │    │
│  │                 increment_download_count()        │    │
│  │                 prune_old_search_queries()        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Supabase Auth                                    │    │
│  │  email/password for admin                        │    │
│  │  anon access for public users                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Supabase Storage                                 │    │
│  │  bucket: papers (public)                         │    │
│  │  CDN URLs for PDF delivery                       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                       Vercel                             │
│            Static hosting for React SPA                  │
│            vercel.json SPA fallback routing              │
│            Auto-deploy from GitHub main branch           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Complete Endpoint Mapping Table

### Public Endpoints

| Current FastAPI Endpoint | Current Logic | Supabase Replacement |
|---|---|---|
| `GET /api/v1/classes` | Query all rows from `classes` table with subject count | `supabase.from('classes').select('*, subjects(count)')` |
| `GET /api/v1/classes/{id}` | Query single class by ID | `supabase.from('classes').select('*, subjects(count)').eq('id', id).single()` |
| `GET /api/v1/classes/{id}/subjects` | Query subjects for class, count visible papers each | `supabase.from('subjects').select('*, papers(count)').eq('class_id', id).order('display_order')` |
| `GET /api/v1/subjects/{id}` | Query subject with class join, count visible papers | `supabase.from('subjects').select('*, classes(*)').eq('id', id).single()` |
| `GET /api/v1/subjects/{id}/papers` | Query visible papers for subject, optional filters | `supabase.from('papers').select('*').eq('subject_id', id).eq('is_visible', true).order('year', {ascending: false})` |
| `GET /api/v1/papers/recent` | Query visible papers ordered by `created_at DESC` | `supabase.from('papers').select('*').eq('is_visible', true).order('created_at', {ascending: false}).limit(10)` |
| `GET /api/v1/papers/popular` | Query visible papers ordered by `download_count DESC` | `supabase.from('papers').select('*').eq('is_visible', true).order('download_count', {ascending: false}).limit(10)` |
| `GET /api/v1/papers/{id}` | Query single visible paper with subject+class join | `supabase.from('papers').select('*, subjects(*, classes(*))').eq('id', id).eq('is_visible', true).single()` |
| `GET /api/v1/papers/by-slug/{slug}` | Extract numeric ID from slug suffix, query paper | Extract ID from slug (`slug.split('-').at(-1)`), then same as `papers/{id}` |
| `GET /api/v1/exam-types` | Returns hardcoded list of 9 exam types | **Hardcode as a constant in frontend** — no DB needed |
| `POST /api/v1/papers/{id}/download` | Increment `download_count` by 1 | `supabase.rpc('increment_download_count', { paper_id_param: id })` — RPC already written in `004_functions.sql` |
| `GET /api/v1/search` | ILIKE query across title, exam_type, subject.name, class.name with alias expansion | `supabase.from('papers').select('*, subjects(name, classes(name))').eq('is_visible', true).or('title.ilike.%q%,exam_type.ilike.%q%')` + insert row into `search_queries` table |

### Admin Endpoints

| Current FastAPI Endpoint | Current Logic | Supabase Replacement |
|---|---|---|
| `POST /api/v1/auth/login` | Check `admins` table, verify bcrypt hash, return JWT | `supabase.auth.signInWithPassword({ email, password })` → returns session with access token |
| `GET /api/v1/admin/me` | Decode JWT, fetch admin row from `admins` | `supabase.auth.getUser()` → returns auth user object |
| `GET /api/v1/admin/stats` | 7 separate COUNT queries aggregated | `supabase.rpc('get_admin_stats')` — already written in `004_functions.sql` |
| `GET /api/v1/admin/papers` | Return all papers regardless of `is_visible` | `supabase.from('papers').select('*').order('created_at', {ascending: false})` — RLS allows authenticated users to see all |
| `POST /api/v1/admin/papers` | Validate file, upload to storage, insert DB row | `supabase.storage.from('papers').upload(filename, file)` → get public URL → `supabase.from('papers').insert({...})` |
| `PUT /api/v1/admin/papers/{id}` | Update metadata fields on paper row | `supabase.from('papers').update({title, youtube_url, is_visible, ...}).eq('id', id)` |
| `DELETE /api/v1/admin/papers/{id}` | Delete storage file + delete DB row | `supabase.storage.from('papers').remove([file_path])` → `supabase.from('papers').delete().eq('id', id)` |
| `GET /api/v1/admin/search-analytics` | Return in-memory deque/dict analytics | `supabase.rpc('get_search_analytics')` — already written in `004_functions.sql` |
| `GET /api/v1/admin/recent-uploads` | Query last 20 papers with subject+class | `supabase.from('papers').select('*, subjects(name, classes(name))').order('created_at', {ascending: false}).limit(20)` |
| `GET /api/v1/admin/content-status` | Coverage matrix across all classes/subjects/exam_types | `supabase.rpc('get_content_status')` — already written in `004_functions.sql` |
| `GET /api/v1/admin/audit-logs` | Query `audit_logs` table with optional action filter | `supabase.from('audit_logs').select('*').order('created_at', {ascending: false}).limit(50)` |

---

## 4. Files That Must Change

### Services — Complete Replacement
| File | Action |
|---|---|
| `frontend/src/services/api.js` | Replace Axios client with Supabase client singleton |
| `frontend/src/services/admin.js` | Replace all Axios calls with Supabase calls |
| `frontend/src/services/classes.js` | Replace with Supabase queries |
| `frontend/src/services/subjects.js` | Replace with Supabase queries |
| `frontend/src/services/papers.js` | Replace with Supabase queries |
| `frontend/src/services/search.js` | Replace with Supabase query + insert to `search_queries` |

### Auth — Complete Replacement
| File | Action |
|---|---|
| `frontend/src/contexts/AuthContext.jsx` | Replace JWT localStorage logic with `supabase.auth.onAuthStateChange()` |
| `frontend/src/components/admin/ProtectedRoute.jsx` | Check Supabase session instead of token existence |
| `frontend/src/pages/admin/LoginPage.jsx` | Call `supabase.auth.signInWithPassword()` instead of `/auth/login` |

### Pages — Minimal Changes (interface-compatible)
| File | Change Required |
|---|---|
| `frontend/src/pages/admin/DashboardPage.jsx` | Update `getStats` call signature |
| `frontend/src/pages/admin/PapersPage.jsx` | Update upload form to use Supabase Storage directly |
| `frontend/src/pages/admin/BulkUploadTab.jsx` | Update upload logic to use Supabase Storage |
| All other pages | No changes if service function signatures are preserved |

### New File Required
| File | Purpose |
|---|---|
| `frontend/src/lib/supabase.js` | Supabase client singleton (URL + anon key from env) |

### Files to Delete
| File | Reason |
|---|---|
| `backend/` (entire directory) | FastAPI backend eliminated |
| `Dockerfile` (root) | No longer needed |
| `backend/Dockerfile` | No longer needed |
| `docker-compose.yml` | No longer needed |
| `Procfile` | No longer needed |
| `change_admin_password.py` | Replaced by Supabase Auth dashboard |
| `frontend/src/services/api.js` | Replaced by supabase.js client |

---

## 5. What Stays Identical

- All React page UI components — zero visual changes
- All TailwindCSS styles
- All routing (`react-router-dom`)
- All public page layouts and admin layouts
- `frontend/index.html`, `vite.config.js`, `package.json` (with `@supabase/supabase-js` added)
- Supabase Storage bucket structure and PDF URLs
- All 5 SQL migration files (`001`–`005`) — already designed for this exact architecture
- All RPC functions (`get_admin_stats`, `get_search_analytics`, `get_content_status`, `increment_download_count`)
