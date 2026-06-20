# Dependency Audit — TN State Board Learning Platform

Audit performed against the actual codebase. All imports verified by source inspection.

---

## Backend — `backend/requirements.txt`

### Status: CORRECT (with version pinning notes)

| Package             | Version Used | Used In                              | Status    |
|---------------------|-------------|--------------------------------------|-----------|
| fastapi             | 0.115.0     | `main.py`, all routers               | ✅ Required |
| uvicorn[standard]   | 0.30.6      | Process runner                       | ✅ Required |
| sqlalchemy          | 2.0.35      | `database.py`, all models/services   | ✅ Required |
| psycopg2-binary     | 2.9.9       | PostgreSQL adapter for SQLAlchemy    | ✅ Required |
| pydantic            | 2.9.2       | All `schemas.py` models              | ✅ Required |
| pydantic-settings   | 2.5.2       | Config management                    | ✅ Required |
| PyJWT               | 2.9.0       | `services/auth.py` — token encode/decode | ✅ Required |
| werkzeug            | ≥3.1.0      | `services/auth.py` — password hashing | ✅ Required |
| python-multipart    | 0.0.12      | FastAPI file upload form parsing     | ✅ Required |
| python-dotenv       | 1.0.1       | `config.py` — loads `.env`           | ✅ Required |
| supabase            | 2.31.0      | `services/storage.py` (optional)     | ✅ Required (lazy-imported, only when STORAGE_BACKEND=supabase) |

### Version Conflict Fixed
During Replit setup, `requirements.txt` pinned `PyJWT==2.9.0` and `pydantic==2.9.2`, but `supabase==2.31.0` requires `PyJWT>=2.12.0` and `pydantic>=2.11.7`. The installed environment resolves to:
- `PyJWT==2.13.0`
- `pydantic==2.11.x`

**Recommendation:** Update `requirements.txt` to use compatible ranges:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
pydantic>=2.11.7,<3.0
pydantic-settings>=2.5.2,<3.0
PyJWT>=2.12.0,<3.0
werkzeug>=3.1.0
python-multipart==0.0.12
python-dotenv>=1.0.1
supabase==2.31.0
```

### Missing packages
None. All imports in the backend source resolve to packages in `requirements.txt`.

### Unused packages in `requirements.txt`
None found. All packages are actively used.

---

## Root `pyproject.toml` — STALE / LEGACY

The root `pyproject.toml` was generated for the original Flask-based project and lists packages that are **not used by the current FastAPI application**.

| Package          | Status in current app | Action              |
|------------------|-----------------------|---------------------|
| flask            | ❌ Not imported anywhere | Remove              |
| flask-sqlalchemy | ❌ Not imported anywhere | Remove              |
| email_validator  | ❌ Not used            | Remove              |
| matplotlib       | ❌ Not used            | Remove              |
| numpy            | ❌ Not used            | Remove              |
| openai           | ❌ Not used            | Remove              |
| pillow           | ❌ Not used            | Remove              |
| gunicorn         | ⚠️ Deployment tool     | Keep only if needed |
| psycopg2-binary  | ✅ Used by backend     | Keep                |
| python-dotenv    | ✅ Used by backend     | Keep                |
| sqlalchemy       | ✅ Used by backend     | Keep                |
| werkzeug         | ✅ Used by backend     | Keep                |

> **Note:** The root `pyproject.toml` is the Replit environment manifest, not the FastAPI app's dependency file. The canonical dependency file is `backend/requirements.txt`. The legacy Flask packages in `pyproject.toml` do not affect the running app but add install overhead and confusion.

---

## Frontend — `frontend/package.json`

### Runtime Dependencies

| Package          | Version  | Used In                              | Status    |
|------------------|----------|--------------------------------------|-----------|
| axios            | ^1.7.7   | All `services/*.js` API calls        | ✅ Required |
| react            | ^18.3.1  | All components                       | ✅ Required |
| react-dom        | ^18.3.1  | `main.jsx` render                    | ✅ Required |
| react-router-dom | ^6.27.0  | `router/index.jsx` + all pages       | ✅ Required |

### Dev Dependencies

| Package               | Version   | Purpose                       | Status    |
|-----------------------|-----------|-------------------------------|-----------|
| @vitejs/plugin-react  | ^4.3.2    | Vite JSX transform            | ✅ Required |
| autoprefixer          | ^10.4.20  | Tailwind PostCSS processing   | ✅ Required |
| postcss               | ^8.4.47   | CSS processing pipeline       | ✅ Required |
| tailwindcss           | ^3.4.14   | Utility CSS framework         | ✅ Required |
| vite                  | ^5.4.10   | Build tool + dev server       | ✅ Required |

### Missing packages
None. All imports resolve correctly.

### Unused packages
None found.

---

## Flask / Legacy Code Check

Searched entire repository for Flask imports and references in active source files:

| Search Pattern      | Backend (`backend/`) | Frontend (`frontend/`) | Root Python files |
|---------------------|----------------------|------------------------|-------------------|
| `import flask`      | ❌ Not found          | N/A                    | ❌ Not found       |
| `from flask`        | ❌ Not found          | N/A                    | ❌ Not found       |
| `Flask(`            | ❌ Not found          | N/A                    | ❌ Not found       |
| `app.route`         | ❌ Not found          | N/A                    | ❌ Not found       |
| `templates/`        | ❌ Not found          | N/A                    | ❌ Not found       |
| `render_template`   | ❌ Not found          | N/A                    | ❌ Not found       |
| `static/`           | ❌ Not found          | N/A                    | ❌ Not found       |

**Result: The backend is entirely Flask-free.** All references to Flask exist only in:
- `pyproject.toml` (legacy Replit manifest — stale deps)
- `.gitignore` (Flask-specific stanzas — harmless but outdated)
- Documentation/report files in `archive/` and root

---

## Recommendations

1. **Update `backend/requirements.txt`** — loosen version pins to resolve supabase/pydantic/PyJWT conflict.
2. **Clean `pyproject.toml`** — remove `flask`, `flask-sqlalchemy`, `email_validator`, `matplotlib`, `numpy`, `openai`, `pillow`.
3. **Update `.gitignore`** — remove Flask-specific stanzas (`.flaskenv`, `instance/`), add `frontend/dist/`, `frontend/node_modules/`, `.pythonlibs/`.
