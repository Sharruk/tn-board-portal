# Vercel Deployment Simulation
## TN State Board Learning Platform — React + Supabase + Vercel

---

## Environment Variables

### Vercel Dashboard → Project → Settings → Environment Variables

| Variable Name | Value | Environments |
|---|---|---|
| `VITE_SUPABASE_URL` | `https://xxxxxxxxxxxx.supabase.co` | Production, Preview, Development |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGci...` (anon/public key) | Production, Preview, Development |

**Total: 2 variables.** The current FastAPI architecture requires 7+:
`DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `STORAGE_BUCKET`, `CORS_ORIGINS`, `API_URL`, `STORAGE_BACKEND`.

> Security note: The `VITE_` prefix embeds these values in the JavaScript bundle at build time. The `anon` key is **designed** to be public — Supabase RLS policies enforce all access control at the database level. The `service_role` key (which bypasses RLS) must never be used here.

### Local Development — `frontend/.env.local`

```
VITE_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

This file is `.gitignored` (Vite's default). It is never committed to version control.

---

## Supabase Project Configuration

### Settings → API (collect these)

| Key | Location in Supabase Dashboard |
|---|---|
| `VITE_SUPABASE_URL` | Settings → API → Project URL |
| `VITE_SUPABASE_ANON_KEY` | Settings → API → Project API keys → `anon` (public) |

### Authentication → URL Configuration (set these after first Vercel deploy)

| Setting | Value |
|---|---|
| Site URL | `https://your-app.vercel.app` (or custom domain) |
| Redirect URLs | `https://your-app.vercel.app/**` |

---

## Vercel Build Configuration

### Detected automatically (if `frontend/` is set as root directory)

| Setting | Value |
|---|---|
| Framework Preset | Vite (auto-detected from `vite.config.js`) |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |
| Node.js Version | 18.x (Vercel default) |

### `package.json` scripts (confirmed from actual file)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```

`npm run build` → `vite build` → outputs to `frontend/dist/`.

---

## Routing Configuration

### `frontend/vercel.json` (post-migration)

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

This single rule makes Vercel serve `index.html` for every path, enabling React Router's client-side routing. Without this, any direct URL access to `/class/10` or `/admin/dashboard` would return a 404.

**Current `frontend/vercel.json` (broken — must be replaced):**
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "REPLACE_WITH_RAILWAY_URL/api/$1" }
  ]
}
```
The current file has a placeholder `REPLACE_WITH_RAILWAY_URL` and routes `/api/*` to a non-existent backend. After migration, this must be replaced with the SPA rewrite above.

---

## Expected Vercel Project Structure

```
Vercel Project
├── Root Directory: frontend/
│
├── Build Phase:
│   ├── npm install          → installs from frontend/package.json
│   ├── npm run build        → vite build
│   └── Output: frontend/dist/
│       ├── index.html
│       ├── assets/
│       │   ├── index-[hash].js     (React app bundle)
│       │   ├── index-[hash].css    (Tailwind output)
│       │   └── vendor-[hash].js    (React, React-Router, Supabase SDK)
│       └── (any public/ assets)
│
├── Routing:
│   ├── /                    → dist/index.html (React Router takes over)
│   ├── /class/10            → dist/index.html (React Router renders ClassPage)
│   ├── /admin/login         → dist/index.html (React Router renders LoginPage)
│   ├── /search?q=maths      → dist/index.html (React Router renders SearchPage)
│   └── /api/*               → DOES NOT EXIST (no proxy, no backend)
│
└── CDN:
    └── All static assets served from Vercel's global CDN
        PDF files served from Supabase Storage CDN
        (separate origin: https://*.supabase.co/storage/v1/object/public/papers/*)
```

---

## Build Output Simulation

Estimated bundle sizes after migration (Vite production build):

| Asset | Estimated Size | Notes |
|---|---|---|
| `index.html` | ~1 KB | Entry point |
| `index-[hash].css` | ~20–40 KB (gzip) | Tailwind purged output |
| `vendor-[hash].js` | ~150–200 KB (gzip) | React 18 + React Router + Supabase JS |
| `index-[hash].js` | ~80–120 KB (gzip) | App code: all pages, components, services |
| **Total first load** | **~250–360 KB (gzip)** | Excellent for a student portal |

Supabase JS SDK adds approximately 70 KB gzip vs Axios's ~15 KB gzip. Net increase: ~55 KB. Negligible on modern connections.

---

## Environment Variable Propagation

```
Supabase Dashboard
    │
    │  Copy URL + anon key
    ▼
Vercel Dashboard
    → Settings → Environment Variables
    → VITE_SUPABASE_URL = https://xxxx.supabase.co
    → VITE_SUPABASE_ANON_KEY = eyJ...
    │
    │  git push triggers build
    ▼
Vercel Build Runner
    → npm install
    → npm run build
    → Vite inlines import.meta.env.VITE_* at build time
    → Values baked into index-[hash].js
    │
    ▼
Deployed site
    → Browser downloads index-[hash].js
    → supabase.js: createClient(BAKED_IN_URL, BAKED_IN_ANON_KEY)
    → All Supabase calls use these baked-in values
```

---

## Deployment Sequence

```
Step 1: Supabase setup complete (migrations applied, admin user created, bucket configured)
            ↓
Step 2: Code migration complete (frontend only, no backend)
            ↓
Step 3: git add . && git commit && git push
            ↓
Step 4: Vercel detects push → starts build (2–3 minutes)
            ↓
Step 5: Vercel build succeeds → deployment live at https://your-app.vercel.app
            ↓
Step 6: Set Supabase Auth Site URL to the Vercel domain
            ↓
Step 7: Smoke test — homepage, class page, admin login, upload, delete
            ↓
Step 8: Drop admins table in Supabase SQL Editor
            ↓
Step 9: Delete backend/ directory → git push → Vercel redeploys (no change to frontend)
            ↓
Complete.
```

---

## Auto-Deploy on Push

After the initial setup, every `git push` to the main branch triggers:
1. Vercel builds `frontend/` with `npm run build`
2. Deploys the new `dist/` output
3. Zero-downtime swap to new deployment

Pull requests get automatic preview URLs (e.g., `https://your-app-git-feature-branch.vercel.app`).

---

## What Does NOT Exist After Migration

| Endpoint | Status |
|---|---|
| `GET /api/v1/classes` | ❌ Eliminated — data comes from Supabase directly |
| `POST /api/v1/auth/login` | ❌ Eliminated — Supabase Auth handles this |
| `POST /api/v1/admin/papers` | ❌ Eliminated — upload goes directly to Supabase Storage |
| `GET /uploads/*` | ❌ Eliminated — all PDFs served from Supabase CDN |
| Any server process | ❌ None — pure static site + Supabase BaaS |

---

## Vercel Free Tier Limits (Monthly)

| Resource | Free Limit | Expected Usage | Headroom |
|---|---|---|---|
| Bandwidth | 100 GB | <1 GB (static assets only; PDFs served by Supabase) | 99%+ |
| Build minutes | 6,000 min | ~3 min/deploy, 10 deploys/month = 30 min | 99%+ |
| Serverless functions | 100 GB-hours | None used (static site) | 100% |
| Deployments | Unlimited | 10–20/month | Unlimited |
| Custom domains | Unlimited | 1 | Unlimited |
