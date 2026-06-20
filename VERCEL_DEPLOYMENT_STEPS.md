# Vercel Deployment Steps
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Prerequisite:** All steps in `SUPABASE_DEPLOYMENT_CHECKLIST.md` must be completed first.

---

## Pre-Deployment Checklist

Before deploying to Vercel, confirm all of the following are done in Supabase:

- [ ] Migration 001 applied (tables exist)
- [ ] Migration 002 applied (4 classes, 32 subjects seeded)
- [ ] Migration 003 applied (RLS policies — 13 policies)
- [ ] Migration 004 applied (4 RPC functions)
- [ ] Migration 005 applied (analytics index + view + cleanup function)
- [ ] Migration 006 applied (`search_papers` RPC)
- [ ] `papers` storage bucket created (public, 50 MB limit, PDF only)
- [ ] Storage RLS policies applied
- [ ] Admin user created in Authentication

---

## Option A — Deploy via GitHub (Recommended)

### Step 1 — Push to GitHub

If the repo is not yet on GitHub:

1. Go to [github.com/new](https://github.com/new)
2. Create a new repository (public or private)
3. In your Replit shell, initialize and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

> If git is already connected to GitHub, just push:
```bash
git push origin main
```

---

### Step 2 — Import to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your GitHub repository
4. Click **Import**

---

### Step 3 — Configure Build Settings

When prompted, set:

| Setting | Value |
|---|---|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` *(auto-detected)* |
| **Output Directory** | `dist` *(auto-detected)* |
| **Install Command** | `npm install` *(auto-detected)* |

> **Root Directory is critical.** The React app lives in `frontend/`, not the repo root.  
> Setting this correctly means Vercel reads `frontend/vercel.json` for the SPA rewrite rule.

---

### Step 4 — Set Environment Variables

In the same import screen, click **"Environment Variables"** and add:

| Name | Value | Environments |
|---|---|---|
| `VITE_SUPABASE_URL` | `https://fcxvrsgcvmlowehpilvr.supabase.co` | Production, Preview, Development |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Production, Preview, Development |

> These must be set **before** the first deploy, because Vite bakes them into the JS bundle at build time.

---

### Step 5 — Deploy

Click **"Deploy"**.

Vercel will:
1. Clone the repo
2. `cd frontend && npm install`
3. `npm run build` (produces `frontend/dist/`)
4. Serve `frontend/dist/` from a global CDN
5. Apply the SPA rewrite from `frontend/vercel.json`

Expected build output in Vercel logs:
```
✓ 105 modules transformed.
dist/index.html     0.57 kB
dist/assets/*.css   35.40 kB
dist/assets/*.js    529.94 kB
✓ built in ~4s
```

---

### Step 6 — Confirm Deployment URL

Vercel assigns a URL like:
```
https://tn-board-platform.vercel.app
```

All routes will work:
- `/` — Homepage
- `/class/10` — Class page
- `/subject/3` — Subject page
- `/search?q=maths` — Search
- `/admin/login` — Admin login
- `/admin/dashboard` — Protected dashboard

---

## Option B — Deploy via Vercel CLI

If you prefer CLI over the dashboard:

```bash
# Install Vercel CLI (run once)
npm i -g vercel

# From the repo root
cd frontend
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? (your account)
# - Link to existing project? No
# - Project name? tn-board-platform (or any name)
# - In which directory is your code located? ./ (you're already in frontend/)
# - Override settings? Yes
#   - Build Command: npm run build
#   - Output Directory: dist
#   - Development Command: npm run dev

# Set environment variables
vercel env add VITE_SUPABASE_URL
vercel env add VITE_SUPABASE_ANON_KEY

# Deploy to production
vercel --prod
```

---

## Post-Deployment Verification

After deploy, test each route in the browser:

### Public routes
| URL | Expected result |
|---|---|
| `https://YOUR_DOMAIN.vercel.app/` | Homepage with 4 class cards |
| `https://YOUR_DOMAIN.vercel.app/class/9` | Class 9 subjects list |
| `https://YOUR_DOMAIN.vercel.app/class/10` | Class 10 subjects list |
| `https://YOUR_DOMAIN.vercel.app/search?q=maths` | Search results (empty until papers uploaded) |
| `https://YOUR_DOMAIN.vercel.app/admin/login` | Admin login form |

### Deep-link / refresh test (SPA routing)
Open these URLs directly in a new tab (not via navigation):
- `https://YOUR_DOMAIN.vercel.app/class/10` — must load, not 404
- `https://YOUR_DOMAIN.vercel.app/admin/login` — must load, not 404

If these return 404, the SPA rewrite in `frontend/vercel.json` is not being applied — re-check that **Root Directory** is set to `frontend` in Vercel settings.

### Admin panel
| Step | Expected |
|---|---|
| Go to `/admin/login` | Login form appears |
| Enter admin email + password | Redirects to `/admin/dashboard` |
| Dashboard → Stats | Shows 0 papers, 32 subjects, 4 classes |
| Dashboard → Content Status | Shows class/subject grid |
| Papers → Upload | Upload form appears |

---

## Auto-Deploy on Push (GitHub only)

Once connected via GitHub, every `git push` to `main` triggers an automatic rebuild and deploy.

```bash
# Make a change, then:
git add .
git commit -m "your message"
git push origin main
# Vercel deploys automatically within ~60 seconds
```

---

## Custom Domain (Optional)

1. Vercel Dashboard → Project → **Settings** → **Domains**
2. Add your domain (e.g. `tnboard.example.com`)
3. Follow Vercel's DNS configuration instructions
4. HTTPS is automatic — no configuration needed

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Deep links return 404 | Root Directory not set to `frontend` | Vercel → Project Settings → General → Root Directory → set to `frontend` |
| Homepage shows no class cards | Migrations not applied | Run all 6 migrations in Supabase SQL Editor |
| Admin login fails | Admin user not created | Supabase → Authentication → Users → Add user |
| PDF uploads fail | Storage bucket missing | Supabase → Storage → Create `papers` bucket |
| Build error on Vercel | Missing env vars | Check `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` set for all environments |
| All data returns empty | Wrong Supabase URL or key | Verify env vars match Supabase Dashboard → Settings → API |
