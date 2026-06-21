# TN State Board Learning Platform

Free question papers and answer keys for Tamil Nadu State Board students — Classes 9 to 12.

---

## What it does

- Browse question papers and answer keys by class, subject, and exam type
- Search across all content by subject name, exam type, class, or title
- Download PDFs directly from Supabase Storage CDN
- Admin dashboard: upload, edit, toggle visibility, and delete papers
- Audit log of every admin action

---

## Architecture

```
Browser
  React 18 + Vite 5 + Tailwind CSS
        │
        ▼
  Supabase
    PostgreSQL  ← papers, subjects, classes, audit_logs, search_queries
    Auth        ← admin authentication
    Storage     ← PDF files (public CDN)
```

No server-side backend. All data access goes directly from the React frontend
to Supabase via RLS-protected APIs and SECURITY DEFINER RPC functions.

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Frontend | React 18, Vite 5, Tailwind CSS 3    |
| Database | Supabase (PostgreSQL)               |
| Auth     | Supabase Auth                       |
| Storage  | Supabase Storage (public CDN)       |
| Hosting  | Vercel (frontend static deploy)     |

---

## Local Development

### Prerequisites

- Node.js 20+
- A Supabase project (free tier works)

### 1 — Clone and install

```bash
git clone <repo-url>
cd frontend
npm install
```

### 2 — Set environment variables

Create `frontend/.env.local`:

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### 3 — Run

```bash
npm run dev      # http://localhost:5000
```

### 4 — Build

```bash
npm run build    # outputs to frontend/dist/
```

---

## Database Setup

Apply the migrations in order using the Supabase SQL Editor:

| File | Purpose |
|------|---------|
| `supabase/migrations/001_schema.sql` | Tables: classes, subjects, papers, audit_logs, search_queries |
| `supabase/migrations/002_seed_data.sql` | Seed data: classes 9–12, all subjects |
| `supabase/migrations/003_rls_policies.sql` | Row Level Security policies |
| `supabase/migrations/004_functions.sql` | RPC: increment_download_count, get_admin_stats, get_content_status |
| `supabase/migrations/005_search_analytics.sql` | Search analytics support |
| `supabase/migrations/006_search_rpc.sql` | RPC: search_papers |

---

## Environment Variables

| Variable | Where to set | Description |
|---|---|---|
| `VITE_SUPABASE_URL` | Replit Secrets / `.env.local` / Vercel | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Replit Secrets / `.env.local` / Vercel | Supabase anon/public key |

Both variables are build-time only (Vite embeds them at `npm run build`).
The anon key is safe to expose — Supabase RLS enforces all access control.

---

## Vercel Deployment

1. Push repo to GitHub
2. Import project in [Vercel](https://vercel.com)
3. Set **Root Directory** → `frontend`
4. Add environment variables: `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
5. Deploy — Vercel auto-detects Vite

The `vercel.json` at the repo root handles SPA routing so React Router
routes like `/search` and `/admin` work on direct navigation and refresh.

---

## Admin Access

Admins are managed via Supabase Auth (dashboard → Authentication → Users).
The admin email is used to identify admin sessions in the app.
There is no separate admin registration flow — add users directly in Supabase.

---

## Key Files

```
frontend/src/
├── lib/supabase.js          # Supabase client (reads env vars)
├── contexts/AuthContext.jsx # Auth state via Supabase Auth
├── services/
│   ├── papers.js            # CRUD for papers
│   ├── search.js            # Full-text search via search_papers RPC
│   ├── classes.js           # Fetch classes and subjects
│   └── admin.js             # Admin stats, audit log, content status
├── pages/                   # Public and admin pages
└── router/index.jsx         # Route definitions

supabase/migrations/         # SQL migrations (schema, seed, RLS, functions)
vercel.json                  # SPA rewrite rule for React Router
```
