# ARCHITECTURE_RULES.md — Architecture Rules
# TN Board Portal

> The architecture of this project is intentional and stable. Read and follow these rules precisely.

---

## Architectural Pattern

**Frontend-only SPA + Backend-as-a-Service (BaaS)**

```
Browser (React SPA)
    │  Supabase JS Client (HTTPS)
    ▼
Supabase Platform
    ├── Auth    — JWT session, email/password
    ├── Storage — Three CDN-backed buckets (papers, official-updates, news-media)
    └── Postgres — Tables, RLS policies, custom RPC functions
         ↑
         Vercel (static hosting, global CDN)
```

There is **no custom backend server**. This is a deliberate architectural decision:
- Zero backend maintenance overhead
- RLS enforces authorization at the database level
- Supabase manages Auth, Storage, and DB
- Vercel provides CDN-based static hosting

**Do NOT introduce:**
- Express, Fastify, or any Node.js backend
- Custom API routes (except Vercel serverless functions if strongly justified)
- A separate database outside of Supabase

---

## Layer Responsibilities

### `src/lib/`
Single-instance Supabase client. Nothing else.
- `supabase.js` — `createClient()` with env vars

**Rule:** Only one Supabase client instance exists in the app.

### `src/services/`
**ALL database access lives here.** No exceptions.

| File | Responsibility |
|------|---------------|
| `papers.js` | CRUD for question papers |
| `classes.js` | Fetch class hierarchy |
| `subjects.js` | Fetch subjects per class |
| `notices.js` | CRUD for official notices |
| `news.js` | CRUD for news articles |
| `search.js` | Full-site search via RPCs |
| `admin.js` | Admin stats, audit log, admin helpers |

**Rule:** Pages and components NEVER call Supabase directly. All calls go through `services/`.

### `src/components/`
Reusable UI building blocks. No data fetching.

| File | Purpose |
|------|---------|
| `Navbar.jsx` | Global navigation |
| `Footer.jsx` | Global footer |
| `PaperCard.jsx` | Paper item card |
| `NoticeCard.jsx` | Notice item card |
| `NewsCard.jsx` | News item card |
| `ClassCard.jsx` | Class grid card |
| `SearchBar.jsx` | Shared search input |
| `Breadcrumb.jsx` | Page breadcrumb navigation |
| `LoadingSpinner.jsx` | Loading state indicator |
| `ErrorMessage.jsx` | Error state indicator |
| `admin/AdminLayout.jsx` | Admin section shell |
| `admin/ProtectedRoute.jsx` | Auth guard for admin routes |

**Rule:** Components receive data via props. They do not fetch data independently.

### `src/pages/`
Route-level components. May call services, compose components.

Public pages: `HomePage`, `ClassPage`, `SubjectPage`, `PaperListPage`, `PaperDetailPage`, `OfficialNoticesPage`, `NoticeDetailPage`, `NewsPage`, `NewsDetailPage`, `SearchPage`, `NotFoundPage`

Admin pages (in `pages/admin/`): `LoginPage`, `DashboardPage`, `PapersPage`, `OfficialNoticesPage`, `NewsPage`, `ContentStatusPage`, `BulkUploadTab`

### `src/layouts/`
Layout wrappers that provide Navbar + Footer shells.

| File | Used By |
|------|---------|
| `MainLayout.jsx` | All public pages |
| `components/admin/AdminLayout.jsx` | All admin pages |

### `src/contexts/`
React Context for global state. Currently:
- `AuthContext.jsx` — Supabase Auth session, `login()`, `logout()`, `user`

**Rule:** Do not add new Context providers without a strong reason. Prefer prop passing.

### `src/hooks/`
Custom React hooks for reusable logic:
- `useFetch.js` — Generic data fetching hook

### `src/router/`
All route definitions live here:
- `index.jsx` — `createBrowserRouter` with all public and admin routes

### `src/utils/`
Pure utility functions. No React, no Supabase.
- `download.js` — PDF download helper (creates temporary anchor, triggers browser download)

---

## Data Flow Pattern

### Reading Data (Public)
```
Page component
    → calls service function (e.g., getPublishedPapers())
    → service calls supabase.from(...).select(...)
    → returns { data, error }
    → page renders data or ErrorMessage
```

### Writing Data (Admin)
```
Admin page component
    → calls service function (e.g., uploadPaper(file, metadata))
    → service:
        1. uploads to Supabase Storage
        2. inserts row to database table
        3. inserts row to audit_logs
    → returns { data, error }
    → page shows success/error feedback
```

### Search
```
SearchPage
    → debounced input (400ms)
    → services/search.js → searchAll(term, filters)
    → Promise.all([search_papers RPC, search_notices RPC, search_news RPC])
    → fire-and-forget: log to search_queries table
    → renders tabbed results (Papers | Notices | News)
```

---

## Security Architecture

### Row Level Security (RLS)

Every table has RLS enabled. Rules:

| Table | Public (anon) | Admin (authenticated) |
|-------|---------------|-----------------------|
| `classes` | SELECT | SELECT |
| `subjects` | SELECT | SELECT |
| `papers` | SELECT where status='published' | ALL |
| `official_notices` | SELECT where visible AND not expired | ALL |
| `news_updates` | SELECT where status='published' AND published_at ≤ NOW() | ALL |
| `audit_logs` | None | SELECT (own) |
| `search_queries` | INSERT (via RPC) | ALL |

### Auth
- Admin login: Supabase Auth (email/password)
- Session managed by `AuthContext`
- `ProtectedRoute` wraps all `/admin/*` routes
- No public registration
- Anon key is intentionally public; RLS enforces access, not the key

### Storage
Three public buckets, each with:
- Public SELECT (no auth required for reading files)
- Authenticated INSERT/DELETE (admin only)

---

## Extension Guidelines

When adding a new module (e.g., Study Materials):

1. Create a new migration: `supabase/migrations/015_study_materials.sql`
2. Add a new service: `src/services/studyMaterials.js`
3. Add new page(s): `src/pages/StudyMaterialsPage.jsx`
4. Add new admin page(s): `src/pages/admin/StudyMaterialsPage.jsx`
5. Add components if they are reusable across pages
6. Update router: `src/router/index.jsx`
7. Update admin sidebar in `AdminLayout.jsx`
8. Update `CHANGELOG.md`, `ROADMAP.md`, `docs/ARCHITECTURE.md`
9. Update `CHANGE_HISTORY.md` in `.ai/`

---

## What NOT to Change

- `src/lib/supabase.js` — Never restructure the client singleton
- `src/contexts/AuthContext.jsx` — Session management is stable; extend, don't rewrite
- `src/router/index.jsx` structure — Add routes, never remove existing ones without intent
- `frontend/vite.config.js` — Build config is stable
- `frontend/tailwind.config.js` — Styling config is stable
- `vercel.json` — SPA rewrite is required for React Router to work on direct navigation
