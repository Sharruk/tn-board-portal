# Environment Variables — TN State Board Learning Platform

All variables are read at startup by `backend/app/config.py`. Never commit actual values to version control. Use `.env` locally and your platform's secrets manager in production.

---

## Required Variables

### `DATABASE_URL`
- **Purpose:** PostgreSQL connection string. SQLAlchemy uses this to connect to the database.
- **Format:** `postgresql://USER:PASSWORD@HOST:PORT/DBNAME`
- **Example (dev):** `postgresql://postgres:password@localhost:5432/tnboard`
- **Example (prod):** `postgresql://tnboard_user:strongpass@db.example.com:5432/tnboard`
- **Notes:** If the value starts with `postgres://` it is automatically rewritten to `postgresql://` for SQLAlchemy compatibility. The app raises `RuntimeError` on startup if this is unset.

---

### `JWT_SECRET_KEY`
- **Purpose:** Signs and verifies JWT access tokens for admin authentication.
- **Format:** Long random hex string — minimum 32 characters in production.
- **Example (dev — insecure):** `change-this-secret-in-development`
- **Example (prod):** `a3f8c2e1d7b94f0e6a2c...` (64-char hex)
- **Generate:** `python -c "import secrets; print(secrets.token_hex(32))"`
- **Notes:**
  - In `ENVIRONMENT=production`, the app raises `RuntimeError` if the default insecure value is used.
  - In `ENVIRONMENT=development`, a warning is printed but startup proceeds.
  - Rotating this key invalidates all existing admin sessions.

---

### `CORS_ORIGINS`
- **Purpose:** Comma-separated list of browser origins allowed to call the API.
- **Format:** Comma-separated URLs, or `*` for any origin.
- **Example (dev):** `*`
- **Example (prod):** `https://tnboard.replit.app,https://www.tnboard.example.com`
- **Notes:** In `ENVIRONMENT=production`, `*` causes a `RuntimeError` at startup. Set this to the exact frontend URL(s).

---

## Optional Variables

### `ENVIRONMENT`
- **Purpose:** Controls docs visibility, security enforcement, and SPA serving.
- **Format:** `development` or `production`
- **Default:** `development`
- **Development value:** `development`
- **Production value:** `production`
- **Notes:**
  - `production` disables `/docs`, `/redoc`, `/openapi.json`
  - `production` enables strict checks on `JWT_SECRET_KEY` and `CORS_ORIGINS`
  - `production` activates SPA fallback serving from `frontend/dist/`

---

### `STORAGE_BACKEND`
- **Purpose:** Selects the file storage provider for uploaded PDFs.
- **Format:** `local`, `supabase`, or `s3`
- **Default:** `local`
- **Development value:** `local`
- **Production value:** `supabase` (recommended) or `s3`
- **Notes:**
  - `local` stores files in `uploads/` on the server filesystem. Files are lost on redeploy on ephemeral platforms (Replit, Railway, Heroku).
  - `supabase` requires `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_BUCKET`.
  - `s3` is currently a stub — see `backend/app/services/storage.py` to implement.

---

### `SUPABASE_URL`
- **Purpose:** Base URL of your Supabase project.
- **Format:** `https://<project-id>.supabase.co`
- **Example:** `https://abcdefghijklmnop.supabase.co`
- **Required when:** `STORAGE_BACKEND=supabase`
- **Notes:** Found in Supabase Dashboard → Settings → API → Project URL.

---

### `SUPABASE_SERVICE_ROLE_KEY`
- **Purpose:** Authenticates server-side Supabase API calls (upload, delete, get URL).
- **Format:** Long JWT string starting with `eyJ...`
- **Example:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **Required when:** `STORAGE_BACKEND=supabase`
- **Notes:**
  - Use the **service_role** key, NOT the anon key. The service role bypasses Row Level Security.
  - Found in Supabase Dashboard → Settings → API → `service_role` key.
  - Never expose this in the frontend — only use server-side.

---

### `SUPABASE_BUCKET`
- **Purpose:** Name of the Supabase Storage bucket where PDFs are stored.
- **Format:** String bucket name
- **Default:** `papers`
- **Example (dev):** `papers-dev`
- **Example (prod):** `papers`
- **Notes:** The bucket must exist and be set to **Public** for student download links to work.

---

### `JWT_EXPIRE_MINUTES`
- **Purpose:** Lifetime of admin JWT access tokens.
- **Format:** Integer (minutes)
- **Default:** `60`
- **Development value:** `60`
- **Production value:** `60` (adjust based on security requirements)

---

### `MAX_FILE_SIZE_MB`
- **Purpose:** Maximum allowed PDF upload size.
- **Format:** Integer (megabytes)
- **Default:** `50`
- **Notes:** Enforced in `storage.py`. Supabase also has its own file size limits.

---

## AWS S3 Variables (Future — not yet implemented)

These are only needed if `STORAGE_BACKEND=s3`. The S3 provider is currently a stub.

| Variable               | Purpose                     |
|------------------------|-----------------------------|
| `AWS_ACCESS_KEY_ID`    | AWS IAM access key          |
| `AWS_SECRET_ACCESS_KEY`| AWS IAM secret key          |
| `AWS_S3_BUCKET`        | S3 bucket name              |
| `AWS_S3_REGION`        | S3 bucket region            |

---

## Security Checklist

- [ ] `DATABASE_URL` set in secrets manager, not hardcoded
- [ ] `JWT_SECRET_KEY` is 32+ random characters
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is only set server-side (never in frontend)
- [ ] `CORS_ORIGINS` is set to exact frontend domain in production (not `*`)
- [ ] `ENVIRONMENT=production` is set in the production deployment
- [ ] `.env` file is in `.gitignore` and never committed
