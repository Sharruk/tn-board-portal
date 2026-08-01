# Architecture — TN Board Portal

> Last updated: 2026-07-01 · Version: 1.0.0

---

## High-Level Overview

TN Board Portal is a **server-rendered React SPA** deployed on Vercel, backed entirely by **Supabase** (PostgreSQL + Auth + Storage). There is no custom backend server; all data access goes through the Supabase JavaScript client calling either PostgREST REST endpoints or custom PostgreSQL RPC functions.

```
Browser (React SPA)
    │  Supabase JS Client (HTTPS)
    ▼
Supabase Platform
    ├── Auth    — JWT session, email/password
    ├── Storage — Three CDN-backed buckets (papers, official-updates, news-media)
    └── Postgres — Tables, RLS policies, custom RPC functions
```

---

## Folder Structure

```
tn-board-portal/
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/
│       ├── build.yml
│       ├── lint.yml
│       ├── test.yml
│       ├── preview-deploy.yml
│       ├── production-deploy.yml
│       └── dependency-audit.yml
│
├── docs/
│   └── ARCHITECTURE.md       ← this file
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx              ← App entry point
│       ├── index.css             ← Tailwind directives + global resets
│       │
│       ├── lib/
│       │   └── supabaseClient.js ← Single Supabase createClient() instance
│       │
│       ├── contexts/
│       │   └── AuthContext.jsx   ← Supabase session, login/logout helpers
│       │
│       ├── hooks/                ← Custom React hooks (useAuth, useSearch, …)
│       │
│       ├── router/
│       │   └── index.jsx         ← createBrowserRouter — all route definitions
│       │
│       ├── layouts/
│       │   ├── MainLayout.jsx    ← Navbar + Footer wrapper for public pages
│       │   └── (AdminLayout in components/admin)
│       │
│       ├── components/
│       │   ├── Navbar.jsx
│       │   ├── Footer.jsx
│       │   ├── Breadcrumb.jsx
│       │   ├── ClassCard.jsx
│       │   ├── PaperCard.jsx
│       │   ├── NoticeCard.jsx
│       │   ├── NewsCard.jsx
│       │   ├── SearchBar.jsx
│       │   ├── LoadingSpinner.jsx
│       │   ├── ErrorMessage.jsx
│       │   └── admin/
│       │       ├── AdminLayout.jsx
│       │       └── ProtectedRoute.jsx
│       │
│       ├── pages/
│       │   ├── HomePage.jsx
│       │   ├── ClassPage.jsx
│       │   ├── SubjectPage.jsx
│       │   ├── PaperListPage.jsx
│       │   ├── PaperDetailPage.jsx
│       │   ├── OfficialNoticesPage.jsx
│       │   ├── NoticeDetailPage.jsx
│       │   ├── NewsPage.jsx
│       │   ├── NewsDetailPage.jsx
│       │   ├── SearchPage.jsx
│       │   ├── NotFoundPage.jsx
│       │   └── admin/
│       │       ├── LoginPage.jsx
│       │       ├── DashboardPage.jsx
│       │       ├── PapersPage.jsx
│       │       ├── OfficialNoticesPage.jsx
│       │       ├── NewsPage.jsx
│       │       ├── ContentStatusPage.jsx
│       │       └── BulkUploadTab.jsx
│       │
│       ├── services/             ← ALL Supabase data access lives here
│       │   ├── admin.js          ← Admin stats, audit log, admin CRUD helpers
│       │   ├── classes.js
│       │   ├── subjects.js
│       │   ├── papers.js
│       │   ├── notices.js
│       │   ├── news.js
│       │   └── search.js         ← Calls search_papers, search_notices, search_news RPCs
│       │
│       └── utils/                ← Pure utility functions (slugify, formatDate, …)
│
├── supabase/
│   ├── README.md                ← Migration index and manual setup steps
│   └── migrations/
│       ├── 001_schema.sql       ← classes, subjects, papers, audit_logs, search_queries
│       ├── 002_seed_data.sql    ← Class 9–12 seed rows
│       ├── 003_rls_policies.sql ← RLS for papers and classes/subjects
│       ├── 004_functions.sql    ← get_admin_stats, increment_download_count
│       ├── 005_search_analytics.sql
│       ├── 006_search_rpc.sql   ← search_papers() ILIKE RPC
│       ├── 007_paper_status.sql ← status column (draft|published|archived)
│       ├── 008_official_notices.sql ← official_notices table + RPCs + bucket
│       ├── 009_fix_notices_grants.sql
│       ├── 010_add_youtube_url_to_official_notices.sql
│       ├── 011_news_updates.sql ← news_updates table + RPCs + bucket
│       ├── 012_fix_news_grants.sql
│       ├── 013_preserve_original_filenames.sql
│       └── 014_update_search_papers_rpc.sql
│
├── .env.example                 ← VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
├── .gitignore
├── vercel.json                  ← SPA rewrite: /* → /index.html
├── CHANGELOG.md
├── CONTRIBUTING.md
└── ROADMAP.md
```

---

## Database Schema

### Tables

| Table | Purpose | PK |
|---|---|---|
| `classes` | School classes 9–12 | `id INTEGER` |
| `subjects` | Subjects per class | `id SERIAL` |
| `papers` | Question papers and answer keys | `id SERIAL` |
| `official_notices` | Circulars, timetables, government orders | `id SERIAL` |
| `news_updates` | Education news, exam updates | `id UUID` |
| `audit_logs` | Immutable admin action history | `id SERIAL` |
| `search_queries` | Analytics: every public search term | `id SERIAL` |

### Key Relationships

```
classes  →  subjects  →  papers  →  audit_logs
classes  →  official_notices (nullable)
classes  →  news_updates (nullable)
auth.users → audit_logs (admin_id)
```

### Row Level Security

| Table | anon | authenticated |
|---|---|---|
| `classes` | SELECT | SELECT |
| `subjects` | SELECT | SELECT |
| `papers` | SELECT where `status = 'published'` | ALL |
| `official_notices` | SELECT where `is_visible AND NOT expired` | ALL |
| `news_updates` | SELECT where `status = 'published' AND published_at <= NOW()` | ALL |
| `audit_logs` | None | SELECT (own entries) |
| `search_queries` | INSERT only (via RPC) | ALL |

### PostgreSQL RPC Functions

| Function | Called By | Purpose |
|---|---|---|
| `search_papers(q, p_class_id, p_exam_type, p_paper_type)` | `services/search.js` | Multi-table ILIKE search over papers |
| `search_notices(q, p_category, p_class_id, p_year)` | `services/search.js` | ILIKE search over notices |
| `search_news(q, p_category, p_limit)` | `services/search.js` | ILIKE search over news |
| `get_admin_stats()` | `services/admin.js` | Aggregate statistics for dashboard |
| `increment_download_count(paper_id)` | `services/papers.js` | Atomic download counter increment |
| `record_notice_view(id)` | `services/notices.js` | Notice view counter |
| `record_notice_download(id)` | `services/notices.js` | Notice download counter |
| `increment_news_views(id)` | `services/news.js` | News view counter |

---

## Supabase Storage Buckets

| Bucket | Public | Max File Size | Accepted MIME Types |
|---|---|---|---|
| `papers` | ✅ | Configured in Supabase | `application/pdf` |
| `official-updates` | ✅ | 50 MB | All types (PDF, image, Office docs) |
| `news-media` | ✅ | 20 MB | JPEG, PNG, WebP, GIF, PDF |

All buckets use:
- **Public SELECT** policy for `anon`
- **Authenticated INSERT / DELETE** policy for `authenticated`

---

## Request Flow

### Public Paper Search

```
SearchPage.jsx → useDebounce(400ms)
    → services/search.js → searchAll(term, filters)
        → Promise.all([
            supabase.rpc('search_papers', { q, p_class_id, p_exam_type }),
            supabase.rpc('search_notices', { q, p_category, p_class_id }),
            supabase.rpc('search_news', { q, p_category })
          ])
        → supabase.from('search_queries').insert({ term, result_count }) [fire-and-forget]
    → SearchPage renders tabbed results
```

### Admin Paper Upload

```
PapersPage.jsx (admin) → File input
    → services/admin.js → uploadPaper(file, metadata)
        → supabase.storage.from('papers').upload(uuid_path, file)  [returns public_url]
        → supabase.from('papers').insert({ ...metadata, file_path, public_url, status: 'draft' })
        → supabase.from('audit_logs').insert({ action: 'upload', ... })
    → PapersPage re-fetches and renders updated list
```

---

## Deployment Architecture

```
Developer pushes to GitHub
    │
    ├── PR to develop
    │       ├── GitHub Actions: build.yml → npm run build
    │       ├── GitHub Actions: lint.yml → ESLint
    │       └── Vercel: preview deployment → https://tn-board-portal-<hash>.vercel.app
    │
    └── Merge to main
            ├── GitHub Actions: production-deploy.yml → vercel --prod
            └── GitHub Actions: dependency-audit.yml → npm audit

Production URL: https://tn-board-portal.vercel.app (or custom domain)

Environment variables (Vercel Dashboard → Settings → Environment Variables):
    VITE_SUPABASE_URL        (all environments)
    VITE_SUPABASE_ANON_KEY   (all environments)
    VERCEL_TOKEN             (CI only, in GitHub Secrets)
```

---

## Why These Technology Choices?

| Choice | Reasoning |
|---|---|
| **Supabase** | Managed Postgres with built-in Auth, Storage, RLS, and RPCs — no backend to maintain |
| **Vite** | Fast HMR, ESM-native, small production bundles |
| **React Router v6** | Nested layouts (`AdminLayout`, `MainLayout`) with no extra state management needed |
| **Tailwind CSS** | Rapid styling without context-switching; PostCSS/Autoprefixer pipeline already in Vite |
| **Vercel** | Zero-config SPA hosting, preview URLs per PR, edge CDN |
| **PostgreSQL RPCs** | PostgREST single-table `.or()` cannot filter across JOINs — custom functions solve this |
| **No Redux / Zustand** | Auth context + prop passing is sufficient at current scale; no global state complexity needed |
