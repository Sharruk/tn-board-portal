# Architecture Decision Report
## TN State Board Learning Platform — Vercel Deployment Evaluation

**Date:** 2026-06-20  
**Audit basis:** Live codebase inspection — findings are drawn only from verified source files.  
**Constraint:** Final architecture must be deployable entirely on Vercel (free tier).

---

## Current Feature Inventory

Before evaluating options, every feature in the codebase is catalogued here.  
Each evaluation below is tested against this list.

### Public Features
| Feature | Implementation |
|---------|---------------|
| Homepage with class grid, recent papers, popular papers | `HomePage.jsx` + `GET /papers/recent`, `GET /papers/popular` |
| Browse by Class → Subject → Papers | `ClassPage`, `SubjectPage`, `PaperListPage` + `/classes`, `/subjects` endpoints |
| Paper detail page with PDF viewer + YouTube embed | `PaperDetailPage.jsx` → `public_url` from storage provider |
| Search with alias expansion ("maths" → "mathematics") | `GET /search` in `papers.py`, alias table in Python |
| Filter papers by exam type, year, paper type | Query params on `/subjects/{id}/papers` |
| Download count tracking | `POST /papers/{id}/download` increments DB counter |

### Admin Features
| Feature | Implementation |
|---------|---------------|
| JWT login with IP rate limiting (5 attempts / 15 min) | `auth.py` + `rate_limit.py` — **in-memory dict** |
| Account lockout (5 failures locks DB record for 15 min) | `Admin.locked_until` column, checked on login |
| Audit log (every upload, edit, delete, login recorded) | `AuditLog` table + `audit.py` service |
| Upload PDF with metadata | `POST /admin/papers` — multipart/form-data |
| Bulk upload with filename-based metadata extraction | `BulkUploadTab.jsx` — regex parses filenames client-side, uploads sequentially |
| Edit paper metadata / toggle visibility | `PUT /admin/papers/{id}` |
| Delete paper (file + DB row) | `DELETE /admin/papers/{id}` → calls storage provider `.delete()` |
| Dashboard stats (total papers, downloads, subjects) | `GET /admin/stats` |
| Search analytics (popular/recent queries) | `GET /admin/search-analytics` — **in-memory list** |
| Content status matrix (which subjects/exams have content) | `GET /admin/content-status` |
| Recent uploads list | `GET /admin/recent-uploads` |

### Infrastructure
| Component | Current |
|-----------|---------|
| Backend | FastAPI (Python 3.12), uvicorn |
| Database | PostgreSQL via SQLAlchemy ORM |
| Storage | Abstract provider: local dev / Supabase prod / S3 stub |
| Auth | PyJWT + werkzeug PBKDF2 hashing |
| Frontend | React 18, Vite 5, Tailwind CSS, React Router v6 |
| Hosting | Replit (dev) — no production deployment yet |

---

## Vercel Constraint Analysis

Vercel is a **static + serverless** platform. What it can and cannot do:

| Vercel Capability | Implication |
|------------------|-------------|
| Static file hosting (HTML/JS/CSS) | ✅ React build deploys natively |
| Serverless Functions (Node.js, Python, Go, Rust) | ✅ API logic possible |
| Python Serverless Functions | ⚠️ Available but 50MB bundle limit; no persistent process |
| Long-running processes (uvicorn, gunicorn) | ❌ Not supported |
| Persistent in-memory state between requests | ❌ Each invocation is isolated — cold starts reset memory |
| Local filesystem writes | ❌ Read-only filesystem |
| Request body limit (file uploads) | ⚠️ **4.5 MB default** on Hobby tier |
| Function execution timeout | ⚠️ **10 seconds** on Hobby tier |
| Persistent WebSockets | ❌ Not supported |

**Critical finding for this project:**  
The current FastAPI app uses in-memory state for rate limiting (`rate_limit.py`) and search analytics (`analytics.py`). Both are reset on every serverless cold start and are silently non-functional on Vercel. The **4.5 MB upload limit** blocks PDF uploads on the Hobby tier unless uploads go directly to Supabase from the browser.

---

## Option 1 — React + FastAPI (Current Stack, Adapted for Vercel)

### How it would work on Vercel
- React → Vercel static hosting
- FastAPI → Vercel Python Serverless Functions via `vercel.json` function routing
- Database → External PostgreSQL (Supabase or Neon free tier)
- Storage → Supabase Storage (already the production plan)

### Features Retained
- All public browsing features ✅
- Search with alias expansion (server-side logic preserved) ✅
- Download count tracking ✅
- Audit logging to database ✅
- Account lockout (stored in DB) ✅
- Paper metadata CRUD ✅

### Features Lost / Broken
| Feature | Why |
|---------|-----|
| IP rate limiting | In-memory dict in `rate_limit.py` — resets on every cold start. Would silently fail to rate-limit. |
| Search analytics | In-memory list in `analytics.py` — resets on every cold start. "Popular searches" always shows empty. |
| PDF uploads via admin panel | Vercel 4.5 MB request body limit blocks most PDFs. Would require client-side direct-to-Supabase upload (major refactor). |
| uvicorn server | Cannot run. FastAPI must be restructured as individual function handlers, not a mounted ASGI app. |
| SQLAlchemy connection pool | Connection pooling is designed for long-running servers. Each serverless call creates and tears down DB connections. Requires `NullPool` or pgbouncer. |

### Files Requiring Modification
- `vercel.json` — new, routes all `/api/*` requests to Python function handlers
- `backend/app/main.py` — ASGI app cannot mount; each endpoint needs its own handler file
- `backend/app/services/rate_limit.py` — must be rebuilt as a DB-backed rate limiter
- `backend/app/services/analytics.py` — must be rebuilt to store queries in DB
- `backend/app/database/database.py` — must switch to `NullPool` for serverless
- All admin upload endpoints — must be refactored for client-side direct upload to Supabase
- `pyproject.toml` / `requirements.txt` — `psycopg2-binary` alone is ~12 MB; total bundle may approach 50 MB limit

### Deployment Complexity: **Very High**
FastAPI is not designed for serverless deployment. Adapting it requires restructuring the entire backend from a mounted ASGI app into individual function entry points — effectively rewriting the backend. This is more work than migrating to a native serverless option.

### Estimated Migration Time: **8–14 days**
### Cost: **Free** (Vercel Hobby + Supabase free tier)
### Scalability: **Poor on Hobby** — 10s timeout, 4.5 MB upload limit, cold starts
### Portfolio Value: **Low for this effort** — FastAPI on Vercel is a known anti-pattern; reviewers will recognise it as a forced fit

---

## Option 2 — React + Supabase (Frontend Only)

### How it would work on Vercel
- React → Vercel static hosting (zero config)
- Supabase → PostgreSQL database (direct from browser via Supabase JS client)
- Supabase Auth → admin authentication (replaces JWT + PyJWT)
- Supabase Storage → PDF files (direct browser-to-Supabase upload)
- No backend server at all

### Features Retained
- All public browsing pages ✅
- PDF viewer + YouTube embed ✅
- File upload via admin panel ✅ (direct to Supabase Storage, no 4.5 MB limit)
- Admin login ✅ (Supabase Auth)
- Paper metadata CRUD ✅ (via Supabase JS client + Row Level Security policies)
- Bulk upload (filename parsing is already client-side in `BulkUploadTab.jsx`) ✅
- Content status matrix ✅ (Supabase query)
- Dashboard stats ✅ (Supabase query)
- Recent uploads list ✅ (Supabase query)
- Search ✅ (Supabase full-text search — `to_tsvector` / `websearch_to_tsquery`)
- Download count tracking ✅ (Supabase RPC or row update)

### Features Lost / Significantly Changed
| Feature | Impact |
|---------|--------|
| IP rate limiting | ❌ Lost — no server to track IPs. Supabase Auth has its own brute-force protection on login, but there is no IP-level rate limit for custom logic. |
| Account lockout (custom 5-attempt logic) | ⚠️ Replaced — Supabase Auth has built-in protection but the `failed_login_count` and `locked_until` custom columns are no longer applicable. |
| Audit log (action-level logging) | ⚠️ Can be rebuilt — Admin JS client writes to an `audit_logs` Supabase table on each action. Requires discipline since there is no server-side enforcement. |
| Search alias expansion ("maths" → "mathematics") | ⚠️ Needs rebuild — can be done client-side as a pre-processing step before the Supabase query. Adds ~20 lines of JS. |
| Search analytics (popular/recent queries) | ⚠️ Can be rebuilt — write search terms to a Supabase `search_queries` table from the browser. |
| Custom PBKDF2 password hashing | Replaced by Supabase Auth (bcrypt + salting handled internally). |

### Files Requiring Modification
| File | Change |
|------|--------|
| `backend/` (entire directory) | **Deleted** — no backend |
| `frontend/src/services/api.js` | Rewritten using `@supabase/supabase-js` client |
| `frontend/src/services/admin.js` | Rewritten — all axios calls replaced by Supabase client calls |
| `frontend/src/services/classes.js` | Rewritten |
| `frontend/src/services/subjects.js` | Rewritten |
| `frontend/src/services/papers.js` | Rewritten |
| `frontend/src/services/search.js` | Rewritten (add alias expansion client-side) |
| `frontend/src/contexts/AuthContext.jsx` | Rewritten — use `supabase.auth` instead of localStorage JWT |
| `frontend/src/pages/admin/LoginPage.jsx` | Minor update — call `supabase.auth.signInWithPassword` |
| `frontend/vite.config.js` | Minor — remove proxy config |
| New: `supabase/migrations/001_initial.sql` | Schema + RLS policies |

### Files Unchanged
All React component files (`ClassCard`, `PaperCard`, `Navbar`, `Footer`, `Breadcrumb`, `LoadingSpinner`, `ErrorMessage`), all page layouts (`MainLayout`, `AdminLayout`), all pages (`HomePage`, `ClassPage`, `SubjectPage`, `PaperListPage`, `PaperDetailPage`, `SearchPage`, `NotFoundPage`, `DashboardPage`, `PapersPage`, `BulkUploadTab`, `ContentStatusPage`), the router, and all styling remain unchanged.

### Deployment Complexity: **Low**
1. `npm run build` → push to GitHub → Vercel auto-deploys on every push.
2. Add two environment variables in Vercel: `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
3. Run Supabase SQL migrations once.
4. Done.

### Estimated Migration Time: **3–5 days**
### Cost: **Free**
- Vercel Hobby: $0 — unlimited static deployments
- Supabase free tier: 500 MB PostgreSQL, 1 GB Storage, 50 MB max file size, 2 GB bandwidth/month

### Scalability: **Good for this use case**
Supabase free tier is sufficient for a student portal. Content is read-heavy (students downloading PDFs), which Supabase CDN handles well. Bottleneck would only appear at thousands of concurrent users.

### Portfolio Value: **Good**
Shows: React (component design), Supabase (BaaS, RLS, SQL), Vercel (CI/CD, static hosting). This is a recognisable and in-demand stack.

---

## Option 3 — Next.js + Supabase

### How it would work on Vercel
- Next.js App Router → Vercel (first-class support, zero config)
- Server Components handle public pages (SSR for SEO)
- Server Actions handle admin mutations (secure server-side logic)
- Supabase → database, storage, auth
- No separate backend

### Features Retained
- All public and admin features from Option 2 ✅
- **Plus:** SEO — class, subject, and paper pages are server-rendered with full HTML (Google indexes content)
- **Plus:** Rate limiting — can be implemented in Next.js middleware using Vercel KV (free tier) or a simple in-memory approach per edge worker
- **Plus:** Audit logging in Server Actions (server-side enforcement, not client-side promise)

### Features Lost
- None relative to Option 2. This option adds capabilities rather than removing them.

### Files Requiring Modification
**Everything.** The entire frontend must be rewritten:
- `frontend/` directory → replaced with a new Next.js `app/` directory structure
- All `*.jsx` page files → rewritten as Next.js Server Components or Client Components
- All service files → replaced with Supabase server client calls
- Routing → from React Router `createBrowserRouter` to Next.js file-based routing
- Build tooling → from Vite to Next.js (webpack/turbopack)
- Styling → Tailwind CSS stays, but configuration migrates to Next.js conventions
- Backend → deleted entirely

### Deployment Complexity: **Medium**
Vercel + Next.js is the zero-friction combination — Vercel created Next.js. Deployment itself is easy. The complexity is in the migration.

### Estimated Migration Time: **7–12 days**
This is a complete frontend rewrite. The existing React components cannot be dropped in without changes because Next.js distinguishes Server Components from Client Components and uses file-based routing.

### Cost: **Free**
- Vercel Hobby: $0
- Supabase free tier: $0

### Scalability: **Excellent**
Server-side rendering scales on Vercel's edge network. Supabase has a clear paid upgrade path.

### Portfolio Value: **Excellent**
Next.js + Supabase + Vercel is the highest-signal stack a student can demonstrate in 2025–2026. It shows: SSR/SSG/ISR patterns, Server Actions, edge deployment, BaaS integration, RLS security. Employers recognise it immediately.

---

## Option 4 — Next.js + Supabase + Vercel Functions (Explicit)

### How it would work on Vercel
This is Option 3 with explicit Vercel Edge Functions added as separate API route handlers.

In practice, Next.js API routes (`app/api/*/route.ts`) are already Vercel Functions. Adding "Vercel Functions" explicitly means treating them as standalone endpoints outside the Next.js framework — useful for webhooks, cron jobs, or microservice splits.

For this project's scope, this distinction adds no practical benefit.

### Features Retained / Lost
Identical to Option 3.

### What changes vs Option 3
- Explicit Vercel Edge Middleware for rate limiting (executes at CDN edge, before the function — lower latency, stateless)
- Vercel Cron Jobs for scheduled tasks (e.g., cache warming, analytics rollup) — not currently needed
- More granular function-level configuration (memory, timeout per route)

### Files Requiring Modification
Same as Option 3, plus:
- `vercel.json` — explicit function configuration and cron schedule entries
- `middleware.ts` — edge-level rate limiting logic

### Deployment Complexity: **High**
Edge Functions have significant constraints: no Node.js built-in modules (no `fs`, `crypto`, `net`), limited npm package compatibility, maximum 1 MB bundle size per edge function. Requires careful library selection.

### Estimated Migration Time: **12–18 days**
Longer than Option 3 due to edge function constraints and debugging overhead.

### Cost: **Free** (within Hobby limits)
### Scalability: **Excellent** — edge execution is fastest possible response time
### Portfolio Value: **Excellent but niche** — demonstrates edge computing knowledge, but is overkill for a student project and may raise "over-engineered" flags in reviews

---

## Comparison Matrix

| Criterion | Option 1 (React + FastAPI) | Option 2 (React + Supabase) | Option 3 (Next.js + Supabase) | Option 4 (Next.js + Supabase + Edge) |
|-----------|---------------------------|----------------------------|-------------------------------|--------------------------------------|
| **Vercel compatible** | ⚠️ Forced fit | ✅ Native | ✅ Native | ✅ Native |
| **Deployment complexity** | Very High | Low | Medium | High |
| **Frontend rewrite required** | No | No | Yes (complete) | Yes (complete) |
| **Backend deleted** | No (adapted) | Yes | Yes | Yes |
| **Migration time** | 8–14 days | 3–5 days | 7–12 days | 12–18 days |
| **Free hosting** | ✅ | ✅ | ✅ | ✅ |
| **PDF upload works on free tier** | ❌ (4.5 MB limit) | ✅ (direct to Supabase) | ✅ (direct to Supabase) | ✅ |
| **In-memory state (rate limiting, analytics)** | ❌ Silently broken | ❌ Not possible | ⚠️ Middleware only | ✅ Edge middleware |
| **Audit logging (server-enforced)** | ✅ | ❌ Client-side only | ✅ Server Actions | ✅ |
| **SEO (server-rendered pages)** | ❌ (SPA) | ❌ (SPA) | ✅ | ✅ |
| **React components reused** | ✅ All | ✅ All | ❌ None reused as-is | ❌ None reused as-is |
| **Existing UI unchanged** | ✅ | ✅ | ❌ Rebuild | ❌ Rebuild |
| **Portfolio value** | Low | Good | Excellent | Excellent (niche) |
| **Suitable for student project** | ❌ | ✅ | ✅ | ⚠️ (over-engineered) |

---

## Recommendation

### ✅ Option 2 — React + Supabase

**For the stated priorities (easy deployment, free hosting, minimal maintenance, good portfolio value), Option 2 is the correct choice.**

---

### Justification

**1. Easy deployment**  
Git push → Vercel auto-deploys. No build pipeline to configure. No Docker. No server management. No environment variables beyond two Supabase keys. First deploy takes under 10 minutes.

**2. Free hosting**  
Vercel Hobby tier is permanently free for personal projects. Supabase free tier provides 500 MB PostgreSQL, 1 GB storage, and 2 GB bandwidth — sufficient for thousands of students browsing and downloading papers.

**3. Minimal maintenance**  
There is no server. No uvicorn process to restart. No Python dependency updates to patch. No Dockerfile to maintain. Supabase handles database backups, connection pooling, storage CDN, and auth security automatically.

**4. Good portfolio value**  
React + Supabase + Vercel is a widely recognised and genuinely in-demand stack. A recruiter or senior engineer reviewing the portfolio will see: production deployment, BaaS integration, Row Level Security for access control, direct storage upload, and clean React architecture. The existing components, pages, and layouts — which represent the majority of the UI work — are preserved unchanged.

**5. Practical migration scope**  
Only the services layer changes. The 15 service/context files are rewritten. The 12 page files, 8 component files, router, and all styling are untouched. This is a realistic 3–5 day migration, not a project-level rewrite.

---

### What is Gained vs. Current Stack

| Gain | Detail |
|------|--------|
| PDF uploads work on free tier | Direct browser → Supabase Storage upload — no 4.5 MB serverless limit |
| Zero-config CI/CD | Push to GitHub → Vercel deploys in ~60 seconds |
| Real CDN for PDFs | Supabase Storage serves files via global CDN |
| No server maintenance | No uvicorn, no Dockerfile, no `requirements.txt` dependency drift |
| Built-in auth security | Supabase Auth handles token rotation, refresh, and breach protection |

### What is Lost vs. Current Stack

| Loss | Severity | Mitigation |
|------|----------|-----------|
| IP-based rate limiting | Low | Supabase Auth has built-in brute-force protection on the login endpoint |
| Server-enforced audit logging | Low | Client-side audit writes to Supabase table; sufficient for a student project |
| Custom account lockout columns | Low | Replaced by Supabase Auth's built-in lockout mechanism |
| Search analytics (in-memory) | Low | Write search terms to `search_queries` table from browser — same data, durable |
| FastAPI / Python experience shown | Medium | Offset by Supabase RLS, SQL migrations, and Vercel deployment knowledge |

---

### When to Choose Option 3 Instead

Choose **Option 3 (Next.js + Supabase)** only if:
- SEO is a hard requirement (search engines need to index paper content)
- There is time for a full frontend rewrite (7–12 days)
- The portfolio goal is specifically "demonstrate Next.js knowledge"

Option 3 is strictly better technically, but Option 2 ships faster, is fully functional, and is appropriate for a student project where time and complexity budget matter.

---

### Migration Path: Option 2 Implementation Steps

The following sequence has zero risk of losing the existing UI work:

1. **Create Supabase project** — apply the current SQLAlchemy schema as a SQL migration
2. **Write Supabase RLS policies** — public read on classes/subjects/papers; admin-only write
3. **Replace `AuthContext.jsx`** — swap localStorage JWT for `supabase.auth.signInWithPassword`
4. **Replace 6 service files** — one file per domain (classes, subjects, papers, search, admin, auth) using `@supabase/supabase-js`
5. **Add alias expansion to `search.js`** — 15-line JS dict, same logic as current Python
6. **Update `LoginPage.jsx`** — single line change to call Supabase auth
7. **Update `vite.config.js`** — remove backend proxy
8. **Add Vercel environment variables** — `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
9. **Delete `backend/`** — no longer needed
10. **Push to GitHub** — Vercel deploys automatically

**All 12 page files, 8 component files, router, Tailwind config, and all styling require zero changes.**
