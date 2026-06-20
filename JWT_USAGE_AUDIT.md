# JWT Usage Audit
## TN State Board Learning Platform

**Purpose:** Prove whether `JWT_SECRET_KEY` is still required anywhere in the
current React + Supabase architecture.

**Date:** 2025-06-20  
**Scope:** Entire repository — all files, executed and non-executed.

---

## Summary verdict

> **`JWT_SECRET_KEY` is required only by the FastAPI backend, which is still
> running as a second workflow but is not called by the React frontend.**
>
> The React + Supabase frontend contains **zero JWT references**. Admin auth
> is handled entirely by `supabase.auth.signInWithPassword()`. The FastAPI
> backend reads and validates `JWT_SECRET_KEY` at **startup** (module import
> time) and uses it at the `/api/v1/auth/login` endpoint — but no frontend
> code calls that endpoint.
>
> **If the FastAPI backend workflow is removed, `JWT_SECRET_KEY` is
> completely unnecessary and can be deleted.**  
> **If the FastAPI backend is kept running, `JWT_SECRET_KEY` must be set or
> the backend will emit a warning on every restart (and crash with
> `RuntimeError` if `ENVIRONMENT=production` is also set).**

---

## 1. `JWT_SECRET_KEY`

### Executable code

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| `backend/app/config.py` | 31 | `JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _INSECURE_DEFAULT_SECRET)` | ✅ Yes — runs on every backend startup | ✅ Yes | ⚠️ Only if `ENVIRONMENT=production` and key is missing |
| `backend/app/config.py` | 35–47 | `if JWT_SECRET_KEY == _INSECURE_DEFAULT_SECRET:` → `warnings.warn(...)` / `raise RuntimeError(...)` | ✅ Yes — checked at import | ✅ Yes | ⚠️ `RuntimeError` raised only in production mode |
| `backend/app/config.py` | 49–52 | `if len(JWT_SECRET_KEY) < 32 and IS_PRODUCTION: raise RuntimeError(...)` | ✅ Yes | ✅ Yes | ⚠️ Only in production mode |
| `backend/app/services/auth.py` | 8 | `from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES` | ✅ Yes — imported at startup | ✅ Yes | No |
| `backend/app/services/auth.py` | 30 | `return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)` | ✅ Yes — called on login | ✅ Yes | No |
| `backend/app/services/auth.py` | 78 | `payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])` | ✅ Yes — called on every protected route | ✅ Yes | No |

### Documentation only (not executed)

| File | Lines | Notes |
|------|-------|-------|
| `ENVIRONMENT_VARIABLES.md` | 18, 50, 132 | Reference docs |
| `PRODUCTION_ENVIRONMENT_VARIABLES.md` | 19, 134 | Reference docs |
| `FINAL_DEPLOYMENT_CHECKLIST.md` | 46, 54, 169 | Checklist doc |
| `DOCKER_DEPLOYMENT.md` | 27, 89, 116, 154 | Docker docs |
| `FINAL_DEPLOYMENT_AUDIT.md` | 32 | Audit doc |
| `DEPLOYMENT_GUIDE.md` | 58, 145, 264 | Deployment doc |
| `FINAL_CLEANUP_REPORT.txt` | 176, 179 | Cleanup report |
| `CLEANUP_VERIFICATION.md` | 98 | Verification doc |
| `PHASE1_VERIFICATION_REPORT.md` | 291 | Phase report |
| `AUTH_MIGRATION_PLAN.md` | 38, 96, 196 | Migration plan — **explicitly states `JWT_SECRET_KEY` is "No longer needed"** |
| `README.md` | 96, 114, 173 | README docs |
| `PROJECT_STATUS.txt` | 200 | Status doc |
| `PROJECT_HANDOVER.md` | 52, 71, 93, 138 | Handover doc |
| `GITHUB_READINESS.md` | 37, 43 | GitHub doc |
| `SELF_HOSTING_GUIDE.md` | 83, 94, 276 | Self-hosting doc |
| `RUNNING_GUIDE.md` | 35 | Run guide |
| `VERCEL_DEPLOYMENT_SIMULATION.md` | 16 | Simulation doc |
| `PROJECT_AUDIT_REPORT.txt` | 382, 582 | Audit doc |
| `FINAL_PROJECT_STATE.md` | — | Status doc |
| `ARCHITECTURE_DECISION_REPORT.md` | 122 | Architecture doc |
| `.env.example` | 36 | Example env file — not loaded at runtime |
| `docker-compose.yml` | 27 | Docker compose — not used in Replit |
| `archive/PRODUCTION_READINESS_REPORT.txt` | 35, 45, 185, 190, 202 | Archived |
| `archive/ARCHITECTURE_BLUEPRINT.txt` | 1054 | Archived |
| `attached_assets/Pasted-*.txt` | various | Uploaded reference files — not executed |

---

## 2. `PyJWT`

### Executable code

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| `backend/requirements.txt` | 7 | `PyJWT>=2.12.0,<3.0` | ✅ Yes — installed as dependency | ✅ Yes | No — installs cleanly |
| `backend/app/services/auth.py` | 3 | `import jwt` | ✅ Yes | ✅ Yes | No |
| `backend/app/services/auth.py` | 87 | `except jwt.PyJWTError:` | ✅ Yes — error handler in `get_current_admin()` | ✅ Yes | No |

### Documentation only

| File | Lines | Notes |
|------|-------|-------|
| `PHASE1_VERIFICATION_REPORT.md` | 291 | Reference |
| `README.md` | 46 | Reference |
| `MIGRATION_PLAN.md` | 260 | Migration note |
| `PROJECT_AUDIT_REPORT.txt` | 37, 358 | Audit |
| `FINAL_PROJECT_STATE.md` | 72 | Status |
| `FINAL_DEPLOYMENT_AUDIT.md` | 159 | Audit |
| `FINAL_CLEANUP_REPORT.txt` | 95 | Cleanup |
| `DEPENDENCY_AUDIT.md` | 19, 26, 27, 39, 129 | Dependency audit |
| `ARCHITECTURE_DECISION_REPORT.md` | 46, 122 | Architecture |
| `CLEANUP_EXECUTION_PLAN.md` | 141 | Plan |
| `archive/VALIDATION_REPORT.txt` | 162, 192 | Archived |
| `archive/PHASE3_REPORT.txt` | 143 | Archived |
| `archive/PHASE39_REPORT.txt` | 165, 167 | Archived |
| `attached_assets/Pasted-*.txt` | various | Reference files — not executed |

---

## 3. `jwt.encode`

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| `backend/app/services/auth.py` | 30 | `return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)` | ✅ Yes — called inside `create_access_token()` | ✅ Yes | No |

Documentation only: `AUTH_MIGRATION_PLAN.md:30`, `archive/PHASE39_REPORT.txt:166`

---

## 4. `jwt.decode`

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| `backend/app/services/auth.py` | 78 | `payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])` | ✅ Yes — called inside `get_current_admin()` on every protected FastAPI route | ✅ Yes | No |

Documentation only: `AUTH_MIGRATION_PLAN.md:30`, `archive/PHASE39_REPORT.txt:166`

---

## 5. `Authorization: Bearer`

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| **None in `frontend/src`** | — | Zero matches | — | — | — |

Documentation only: `PROJECT_AUDIT_REPORT.txt:86`, `AUTH_MIGRATION_PLAN.md:28`, `archive/PHASE3_REPORT.txt:29,90,142`, `archive/FRONTEND_PHASE2_REPORT.txt:249`, `docs/API.md:67`

> **Key finding:** No `Authorization: Bearer` header is sent by any file
> in `frontend/src`. The FastAPI bearer scheme (`HTTPBearer`) in
> `backend/app/services/auth.py:12` is defined but never called from the
> React app.

---

## 6. `create_access_token`

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| `backend/app/services/auth.py` | 26 | `def create_access_token(data: dict) -> str:` — definition | ✅ Yes | ✅ Yes | No |
| `backend/app/api/auth.py` | 8 | `from app.services.auth import ... create_access_token ...` | ✅ Yes | ✅ Yes | No |
| `backend/app/api/auth.py` | 89 | `token = create_access_token({"sub": admin.username})` — called on `POST /api/v1/auth/login` | ✅ Yes | ✅ Yes | No |

> `POST /api/v1/auth/login` is a live FastAPI endpoint. It is **not called
> by any file in `frontend/src`**. The frontend uses
> `supabase.auth.signInWithPassword()` exclusively.

---

## 7. `verify_token`

| File | Line | Code | Still executed? | Part of backend? | Blocks deploy? |
|------|------|------|-----------------|-----------------|----------------|
| **No matches anywhere in the repository** | — | — | — | — | — |

---

## 8. Frontend JWT audit (`frontend/src`)

Searched for: `jwt`, `JWT`, `Authorization.*Bearer`, `localStorage.*token`,
`adminToken`, `import.*jwt`, `from.*jwt`.

**Result: zero matches.** The entire `frontend/src` directory contains no
JWT-related code whatsoever.

The frontend admin login flow:

```
frontend/src/pages/admin/AdminLogin.jsx
  → supabase.auth.signInWithPassword({ email, password })
  → Supabase returns a session object (managed by the Supabase SDK)
  → No JWT is stored in localStorage or sent as a Bearer header
```

---

## Conclusion

### Is `JWT_SECRET_KEY` required in the React + Supabase architecture?

**No.** The React frontend is 100% decoupled from JWT. It authenticates via
Supabase Auth and never calls the FastAPI auth endpoints.

### Why does `JWT_SECRET_KEY` currently matter at all?

Because the FastAPI backend (`Backend API` workflow) is still running. Its
`config.py` reads `JWT_SECRET_KEY` at module import time — meaning the
variable is evaluated on every backend startup regardless of whether any
client calls the auth endpoints.

| Condition | Effect |
|-----------|--------|
| Backend workflow running + `ENVIRONMENT=development` (current state) | Warning printed to console; backend starts fine with the insecure default |
| Backend workflow running + `ENVIRONMENT=production` + key missing/default | `RuntimeError` at startup — **backend crashes** |
| Backend workflow **removed** | `JWT_SECRET_KEY` is irrelevant and can be deleted |

### Code-path diagram

```
React Frontend (frontend/src)
  └─ Admin login → supabase.auth.signInWithPassword()   ← Supabase Auth, no JWT
  └─ All data reads → supabase.from(...).select()       ← Supabase RLS, no JWT
  └─ File uploads → supabase.storage.from(...)          ← Supabase Storage, no JWT

FastAPI Backend (backend/) — running but unreachable from frontend
  └─ POST /api/v1/auth/login
       └─ create_access_token()
            └─ jwt.encode(payload, JWT_SECRET_KEY)       ← JWT used here
  └─ All protected routes via get_current_admin()
       └─ jwt.decode(token, JWT_SECRET_KEY)              ← JWT used here
```

### Recommendation

The FastAPI backend is dead code from the perspective of the current
frontend. No frontend page, service, or utility imports `axios` with a
`JWT_SECRET_KEY`-signed token or calls any `/api/v1/*` endpoint.

- **To eliminate `JWT_SECRET_KEY` entirely:** remove the `Backend API`
  workflow and the `backend/` directory.
- **To keep the backend for now:** set `JWT_SECRET_KEY` as a Replit Secret
  to suppress the startup warning. It does not need to be a strong key
  unless the backend login endpoint is ever actually wired to a client.
