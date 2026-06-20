# Production Environment Variables

All variables verified against the live codebase (`backend/app/config.py`, `backend/app/services/storage.py`, `backend/app/services/auth.py`, `frontend/src/services/api.js`).

---

## Backend Variables

### `DATABASE_URL`
| Field | Value |
|-------|-------|
| Required | ✅ Yes — app refuses to start without it |
| Example | `postgresql://tnboard_user:strongpass@db.host:5432/tnboard` |
| Configure on | Railway (via PostgreSQL plugin) · Replit Secrets · Any PostgreSQL host |
| Notes | If value starts with `postgres://`, it is automatically corrected to `postgresql://`. Replit built-in database provides this automatically. |

---

### `JWT_SECRET_KEY`
| Field | Value |
|-------|-------|
| Required | ✅ Yes — app refuses to start in production if using the insecure default |
| Example | `a3f8c2e1d7b94f0e6a2c8d1e5f0b3a7c9d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0` |
| Configure on | Railway · Replit Secrets · Vercel (not needed — backend-only) |
| Generate | `python -c "import secrets; print(secrets.token_hex(32))"` |
| Notes | Minimum 32 characters in production. Rotating invalidates all active admin sessions. |

---

### `ENVIRONMENT`
| Field | Value |
|-------|-------|
| Required | No — defaults to `development` |
| Production value | `production` |
| Configure on | Railway · Replit Secrets |
| Notes | Must be `production` to: disable API docs (`/docs`, `/redoc`), enforce JWT key strength, enforce CORS restrictions, serve React frontend from `frontend/dist/`. |

---

### `CORS_ORIGINS`
| Field | Value |
|-------|-------|
| Required | ✅ Yes in production — `*` raises RuntimeError when `ENVIRONMENT=production` |
| Example | `https://tnboard.replit.app` |
| Example (multiple) | `https://tnboard.replit.app,https://www.tnboard.example.com` |
| Configure on | Railway · Replit Secrets |
| Notes | For Option B (single deployment), frontend and API are on the same domain — CORS is not enforced by the browser. Still set this to the production domain. For Option A (Vercel + Railway), this must be the exact Vercel URL. |

---

### `STORAGE_BACKEND`
| Field | Value |
|-------|-------|
| Required | No — defaults to `local` |
| Production value | `supabase` |
| Configure on | Railway · Replit Secrets |
| Notes | `local` stores files on the server filesystem — files are lost on redeploy on ephemeral platforms. `s3` is a stub (not implemented). Use `supabase` for production. |

---

### `SUPABASE_URL`
| Field | Value |
|-------|-------|
| Required | ✅ Yes when `STORAGE_BACKEND=supabase` |
| Example | `https://abcdefghijklmnop.supabase.co` |
| Configure on | Railway · Replit Secrets |
| Where to find | Supabase Dashboard → Settings → API → Project URL |

---

### `SUPABASE_SERVICE_ROLE_KEY`
| Field | Value |
|-------|-------|
| Required | ✅ Yes when `STORAGE_BACKEND=supabase` |
| Example | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (long JWT string) |
| Configure on | Railway · Replit Secrets |
| Where to find | Supabase Dashboard → Settings → API → `service_role` key |
| ⚠️ Warning | Use the **service_role** key, NOT the `anon` key. Never expose this in the frontend. |

---

### `SUPABASE_BUCKET`
| Field | Value |
|-------|-------|
| Required | No — defaults to `papers` |
| Example | `papers` |
| Configure on | Railway · Replit Secrets |
| Notes | The bucket must already exist in Supabase Storage and be set to **Public**. |

---

### `JWT_EXPIRE_MINUTES`
| Field | Value |
|-------|-------|
| Required | No — defaults to `60` |
| Example | `60` |
| Configure on | Railway · Replit Secrets |
| Notes | Admin session duration in minutes. Lower = more secure, higher = less friction. |

---

### `MAX_FILE_SIZE_MB`
| Field | Value |
|-------|-------|
| Required | No — defaults to `50` |
| Example | `50` |
| Configure on | Railway · Replit Secrets |
| Notes | Maximum PDF upload size in megabytes. Supabase also enforces its own file size limits. |

---

## Frontend Variables (build-time only)

These are injected by Vite at build time using `import.meta.env.VITE_*`.

### `VITE_API_URL`
| Field | Value |
|-------|-------|
| Required | No — defaults to `/api/v1` (relative URL) |
| Option B value | Not needed — relative URL works |
| Option A value | `https://your-backend.up.railway.app/api/v1` |
| Configure on | Vercel (for Option A only) |
| Notes | Only needed for Option A (Vercel + Railway split). For Option B (single deployment), the default `/api/v1` works correctly since frontend and backend are on the same domain. |

---

## Missing Variables Audit

Verified by searching all files in `backend/app/` and `frontend/src/`:

| Variable | Used In | In `.env.example`? | Status |
|----------|---------|-------------------|--------|
| `DATABASE_URL` | `config.py` | ✅ | Complete |
| `JWT_SECRET_KEY` | `config.py` | ✅ | Complete |
| `ENVIRONMENT` | `config.py` | ✅ | Complete |
| `CORS_ORIGINS` | `config.py` | ✅ | Complete |
| `STORAGE_BACKEND` | `config.py`, `storage.py` | ✅ | Complete |
| `SUPABASE_URL` | `storage.py` | ✅ | Complete |
| `SUPABASE_SERVICE_ROLE_KEY` | `storage.py` | ✅ | Complete |
| `SUPABASE_BUCKET` | `storage.py` | ✅ | Complete |
| `JWT_EXPIRE_MINUTES` | `config.py` | ✅ | Complete |
| `MAX_FILE_SIZE_MB` | `config.py` | ✅ | Complete |
| `VITE_API_URL` | `api.js`, `admin.js` | ❌ | Missing from `.env.example` |

**One variable is missing from `.env.example`:** `VITE_API_URL`

---

## Variable Name Corrections

The previous `DEPLOYMENT_GUIDE.md` used incorrect variable names. This has been corrected:

| Wrong (old) | Correct (actual code) | File |
|-------------|----------------------|------|
| `SUPABASE_SERVICE_KEY` | `SUPABASE_SERVICE_ROLE_KEY` | `backend/app/services/storage.py` line 127 |
| `SUPABASE_STORAGE_BUCKET` | `SUPABASE_BUCKET` | `backend/app/services/storage.py` line 128 |
