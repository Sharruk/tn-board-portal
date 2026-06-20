# Deployment Guide — TN State Board Learning Platform

**Version: 2.0 | Updated: 2026-06-20**

---

## Architecture Decision: Option B — Single Deployment (Recommended)

After auditing the codebase, **Option B is strongly recommended**:

```
One server (Replit or Railway)
  ├── FastAPI backend  →  /api/v1/*
  └── React frontend   →  /* (served as static files from frontend/dist/)
```

**Why Option B beats Option A (Vercel + Railway):**

| Factor | Option A (Vercel + Railway) | Option B (Single — Recommended) |
|--------|----------------------------|----------------------------------|
| CORS config | Required (cross-origin) | None needed (same origin) |
| Env vars at build | `VITE_API_URL` must be set | Not needed — relative URLs work |
| Cost | Two paid services | One service |
| Complexity | Two deployments to coordinate | One deployment |
| Code support | Needs vercel.json + rewrites | Already built into `main.py` |

The frontend already uses relative URLs (`/api/v1`). FastAPI already has SPA fallback logic in `main.py` that serves `frontend/dist/index.html` when `ENVIRONMENT=production`.

**Option A (Vercel + Railway) is documented in the appendix** for users who require CDN separation or independent scaling.

---

## Deployment — Option B: Single Deployment on Replit

### Prerequisites

- Supabase account (free tier works) for PDF storage
- Generate a JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`

---

### Step 1 — Set Up Supabase Storage

1. Go to [supabase.com](https://supabase.com) → Create a new project.
2. Navigate to **Storage → New Bucket**.
3. Name it `papers`, check **Public bucket** → Create.
4. Go to **Settings → API**.
5. Copy the **Project URL** and the **service_role** key (not the anon key).

---

### Step 2 — Configure Replit Secrets

In Replit, open **Secrets** (the padlock icon in the sidebar) and add:

| Secret Name | Value |
|-------------|-------|
| `JWT_SECRET_KEY` | A 64-character random hex string |
| `CORS_ORIGINS` | `https://YOUR-APP-NAME.replit.app` |
| `ENVIRONMENT` | `production` |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL` | `https://xxxxxxxxxxxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | The service_role key from Supabase |
| `SUPABASE_BUCKET` | `papers` |

> ⚠️ Set `CORS_ORIGINS` **after** your first deploy — copy the `.replit.app` URL it assigns, then update this secret and redeploy.

---

### Step 3 — Seed the Database

The database must be seeded before the app is functional. Run this in the Replit shell:

```bash
cd backend && python seed.py
```

Expected output:
```
Seeding database...
  + Class: Class 9
  ...
  + Admin created: username=admin / password=admin123
Seed complete.
```

---

### Step 4 — Change the Admin Password

Immediately after seeding, change the default credentials:

```bash
python change_admin_password.py
```

---

### Step 5 — Deploy on Replit

1. Click the **Deploy** button (rocket icon) in Replit.
2. Choose **Autoscale**.
3. Set the **Run command** to:
   ```
   sh -c "cd frontend && npm ci && npm run build && cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 5000"
   ```
4. Ensure `ENVIRONMENT=production` is in Secrets.
5. Click **Deploy**.

> What this command does:
> 1. Builds the React app into `frontend/dist/`
> 2. Starts FastAPI on port 5000
> 3. FastAPI detects `ENVIRONMENT=production` and serves `frontend/dist/` as static files with SPA fallback

---

### Step 6 — Post-Deployment Verification

After deploy completes, verify at `https://your-app.replit.app`:

- [ ] `/health` → `{"status":"healthy"}`
- [ ] `/docs` → 404 (API docs disabled in production ✅)
- [ ] Homepage loads with 4 classes, 32 subjects
- [ ] Navigating to `/search` and refreshing the page does not 404
- [ ] Admin login at `/admin/login` works with the new password
- [ ] Upload a test PDF → confirm it appears in Supabase Storage
- [ ] Download the test PDF → confirm it streams from Supabase CDN
- [ ] Delete the test PDF → confirm removed from Supabase

---

## Deployment — Option A: Vercel (Frontend) + Railway (Backend)

For reference only. Use this if you need separate scaling or a CDN for the frontend.

### Railway Setup (Backend)

1. Create a project at [railway.app](https://railway.app).
2. Connect your GitHub repository.
3. Set **Root Directory** to `backend/`.
4. Railway auto-detects `backend/Dockerfile`.
5. Set environment variables in Railway:
   ```
   DATABASE_URL=postgresql://...  (from Railway PostgreSQL plugin or external)
   JWT_SECRET_KEY=<64-char hex>
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-app.vercel.app
   STORAGE_BACKEND=supabase
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
   SUPABASE_BUCKET=papers
   ```
6. After first deploy, seed via Railway CLI:
   ```bash
   railway run python seed.py
   ```

### Vercel Setup (Frontend)

1. Import the repository at [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend/`.
3. Build settings (auto-detected):
   - Framework: Vite
   - Build command: `npm run build`
   - Output directory: `dist`
4. Set environment variable in Vercel:
   ```
   VITE_API_URL=https://your-backend.up.railway.app/api/v1
   ```
5. **Replace the placeholder in `frontend/vercel.json`:**
   ```json
   {
     "rewrites": [
       { "source": "/api/:path*", "destination": "https://your-backend.up.railway.app/api/:path*" },
       { "source": "/uploads/:path*", "destination": "https://your-backend.up.railway.app/uploads/:path*" },
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```
   Replace `your-backend.up.railway.app` with your actual Railway URL.

6. Deploy.

---

## GitHub Setup

1. Create a repository at github.com.
2. Ensure `.gitignore` excludes `.env`, `frontend/dist/`, `frontend/node_modules/`, `__pycache__/`, `.pythonlibs/`.
3. Push code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
4. **Confirm no secrets are in the repo** before making it public.

---

## Deployment Order

Follow this exact order on first deployment:

1. ✅ Set up Supabase (bucket must exist before first upload)
2. ✅ Set all secrets/environment variables
3. ✅ Deploy the backend (database tables created automatically on startup)
4. ✅ Seed the database (`python seed.py`)
5. ✅ Change admin password (`python change_admin_password.py`)
6. ✅ Deploy the frontend (or trigger a Replit redeploy)
7. ✅ Update `CORS_ORIGINS` with the final frontend URL
8. ✅ Redeploy if `CORS_ORIGINS` changed
9. ✅ Run post-deployment verification checklist

---

## Rollback Procedure

### Replit

1. Open **History** (clock icon in sidebar).
2. Find the last known-good checkpoint.
3. Click **Restore**.
4. Redeploy from the restored state.

### Railway

1. Go to Railway dashboard → your service → **Deployments**.
2. Find the previous successful deployment.
3. Click **Redeploy** on that entry.

### Database Schema Rollback

If a schema change was deployed and you need to revert:

1. Roll back the code first (steps above).
2. Manually revert the schema change via `DATABASE_URL`:
   ```sql
   -- Example: revert an added column
   ALTER TABLE papers DROP COLUMN IF EXISTS new_column;
   ```

---

## Database Migrations

SQLAlchemy `create_all()` runs at every startup and creates **missing tables**. It does **not** add columns to existing tables or remove tables.

**Adding a new column after initial deployment:**
1. Add the column to `backend/app/models/models.py` with `nullable=True` or a default.
2. Run the migration manually before redeploying:
   ```sql
   ALTER TABLE papers ADD COLUMN new_column TEXT DEFAULT NULL;
   ```
3. Deploy — `create_all()` will not conflict with the existing table.

---

## Security Checklist (Before Go-Live)

- [ ] `ENVIRONMENT=production` is set in deployment secrets
- [ ] `JWT_SECRET_KEY` is a random ≥32-character string (not the dev default)
- [ ] `CORS_ORIGINS` is the exact production domain — no `*`
- [ ] Admin default password `admin123` has been changed
- [ ] `STORAGE_BACKEND=supabase` (not `local`)
- [ ] `/docs` returns 404 on the live URL
- [ ] HTTPS is enforced (Replit and Vercel do this automatically)
- [ ] Supabase bucket is **Public** (students need to access PDF URLs directly)
- [ ] Supabase bucket is named exactly `papers` (or matches `SUPABASE_BUCKET`)
