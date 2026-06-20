# Deployment Guide

**TN State Board Learning Platform — v1.0**

This guide walks you through deploying the platform to production on Replit Deployments. Read the entire guide before starting.

---

## Prerequisites

- Replit account with Deployments access
- PostgreSQL database (Replit built-in or external)
- A cloud storage account (Supabase Storage **or** AWS S3) for PDF persistence
- A strong, randomly generated JWT secret key

---

## Step 1 — Set Environment Variables

All sensitive configuration is passed through environment variables. **Never hard-code secrets in source code.**

Set each variable in **Replit → Secrets** before deploying:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `JWT_SECRET_KEY` | ✅ | Random ≥32-char secret for JWT signing |
| `CORS_ORIGINS` | ✅ | Exact frontend URL, e.g. `https://tnboard.replit.app` |
| `ENVIRONMENT` | ✅ | Must be `production` |
| `STORAGE_BACKEND` | ✅ | `local` (dev only) or `s3` / `supabase` |
| `JWT_EXPIRE_MINUTES` | ☐ | Token lifetime in minutes (default: 60) |
| `MAX_FILE_SIZE_MB` | ☐ | PDF size cap in MB (default: 50) |

**Generate a secure JWT secret:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️  The server **refuses to start** in production if `JWT_SECRET_KEY` is still the default value or if `CORS_ORIGINS` is `*`. This is intentional.

---

## Step 2 — Configure Cloud Storage

Local filesystem storage is **not durable** on Replit managed VMs — files are lost on each redeploy. Set up a cloud provider before deploying.

### Option A — Supabase Storage (recommended, free tier available)

1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Storage → New Bucket** → name it `papers` → set to **Public**.
3. Add these secrets in Replit:
   ```
   STORAGE_BACKEND=supabase
   SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
   SUPABASE_SERVICE_KEY=<service role key from Supabase Settings → API>
   SUPABASE_STORAGE_BUCKET=papers
   ```
4. Open `backend/app/services/storage.py` and fill in `SupabaseStorageProvider.save()` and `.delete()` per the implementation guide in the docstring.
5. Install the dependency:
   ```
   pip install supabase
   ```
   Add `supabase>=2.0.0` to `backend/requirements.txt`.

### Option B — AWS S3

1. Create an S3 bucket in the `ap-south-1` (Mumbai) region for low latency.
2. Create an IAM user with `s3:PutObject` and `s3:DeleteObject` on that bucket.
3. Add these secrets in Replit:
   ```
   STORAGE_BACKEND=s3
   AWS_ACCESS_KEY_ID=<your key>
   AWS_SECRET_ACCESS_KEY=<your secret>
   AWS_S3_BUCKET=tnboard-uploads
   AWS_S3_REGION=ap-south-1
   ```
4. Open `backend/app/services/storage.py` and fill in `S3StorageProvider.save()` and `.delete()` per the docstring.
5. Install the dependency:
   ```
   pip install boto3
   ```
   Add `boto3>=1.35.0` to `backend/requirements.txt`.

---

## Step 3 — Change the Admin Password

The default credentials (`admin` / `admin123`) **must** be changed before going live.

Run this once against your production database:

```bash
cd backend
python - <<'EOF'
from app.database.database import SessionLocal
from app.models.models import Admin
from app.services.auth import hash_password

db = SessionLocal()
admin = db.query(Admin).filter(Admin.username == "admin").first()
if admin:
    admin.password_hash = hash_password("YOUR_STRONG_PASSWORD_HERE")
    db.commit()
    print("Password updated.")
else:
    print("No admin found.")
db.close()
EOF
```

---

## Step 4 — Build the Frontend

The production deployment serves the compiled React app from FastAPI as static files.

```bash
cd frontend
npm run build
```

This creates `frontend/dist/` with the compiled assets.

Then mount the dist folder in `backend/app/main.py` by adding **after** the existing `/uploads` mount:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "dist"
)

if os.path.isdir(FRONTEND_DIST):
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    # Catch-all: serve index.html for all non-API routes (React Router)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        index = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index)
```

---

## Step 5 — Deploy on Replit

1. Open **Replit → Deploy** (the rocket icon).
2. Choose **Autoscale** deployment (handles traffic spikes automatically).
3. Set the **Run command** to:
   ```
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```
   *(Replit Deployments use port 8080 by default.)*
4. Click **Deploy**.
5. Replit assigns a `.replit.app` domain. Copy it and update `CORS_ORIGINS` in Secrets.
6. Redeploy once more with the correct `CORS_ORIGINS` value.

---

## Step 6 — Post-Deployment Verification

After the deployment goes live, verify:

- [ ] `https://your-app.replit.app/health` returns `{"status": "healthy"}`
- [ ] `https://your-app.replit.app/docs` returns **404** (docs must be disabled in prod)
- [ ] Homepage loads and subject cards appear
- [ ] Admin login works at `/admin/login` with the **new** password
- [ ] Upload a test PDF and confirm it saves to cloud storage
- [ ] Download the test PDF and confirm it streams correctly
- [ ] Delete the test PDF and confirm the file disappears from cloud storage
- [ ] Content Status page loads with no errors

---

## Database Migrations

The app uses SQLAlchemy `create_all()` at startup — it creates missing tables automatically. There are no manual migrations for the current schema.

**If you add a new column later:**

1. Add it to `backend/app/models/models.py` with a default value or `nullable=True`.
2. Redeploy — SQLAlchemy will NOT auto-add columns to existing tables.
3. Run the migration manually against production:
   ```sql
   ALTER TABLE papers ADD COLUMN new_column TEXT DEFAULT NULL;
   ```
   Connect via Replit's database console or any PostgreSQL client using `DATABASE_URL`.

---

## Rollback Instructions

Replit keeps deployment checkpoints automatically.

**To roll back to a previous version:**
1. Open **Replit → History** (clock icon in the sidebar).
2. Find the last known-good checkpoint.
3. Click **Restore**.
4. Redeploy from the restored checkpoint.

**If the database schema changed and you need to roll back:**
1. Restore the checkpoint first (code rollback).
2. Manually revert any schema changes in the database (e.g. `ALTER TABLE ... DROP COLUMN`).
3. Redeploy.

---

## Environment Variable Reference

See `.env.example` in the project root for a complete, documented list of all environment variables with example values.

---

## Security Checklist (before go-live)

- [ ] `ENVIRONMENT=production` is set
- [ ] `JWT_SECRET_KEY` is a random ≥32-character string
- [ ] `CORS_ORIGINS` is set to the exact production domain (no `*`)
- [ ] Admin default password (`admin123`) has been changed
- [ ] `STORAGE_BACKEND` is `s3` or `supabase` (not `local`)
- [ ] `/docs` and `/redoc` return 404 on the live URL
- [ ] HTTPS is enforced (Replit Deployments handles this automatically)
