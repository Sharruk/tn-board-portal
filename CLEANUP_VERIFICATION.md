# Cleanup Verification — TN State Board Learning Platform

Full-repository scan for legacy code, hardcoded secrets, and stale references. All checks performed against the live codebase.

---

## Flask Imports — Active Source Files

Search: `import flask`, `from flask`, `Flask(`, `app.route`, `render_template`, `send_from_directory`

| File | Flask Reference | Status |
|------|----------------|--------|
| `backend/app/main.py` | None | ✅ Clean |
| `backend/app/config.py` | None | ✅ Clean |
| `backend/app/api/*.py` (5 files) | None | ✅ Clean |
| `backend/app/models/models.py` | None | ✅ Clean |
| `backend/app/schemas/schemas.py` | None | ✅ Clean |
| `backend/app/services/*.py` (5 files) | None | ✅ Clean |
| `backend/app/database/database.py` | None | ✅ Clean |
| `backend/seed.py` | None | ✅ Clean |
| `backend/migrate_41.py` | None | ✅ Clean |
| `change_admin_password.py` | None | ✅ Clean |
| `frontend/src/**` | N/A | ✅ Clean |

**Result: Zero Flask imports in active source code.**

---

## `app.py` References

Search: `app.py`, `from app import app`, `import app`

| File | Reference | Status |
|------|-----------|--------|
| Active Python source files | None | ✅ Clean |
| Root filesystem | `app.py` not present | ✅ Removed |
| `Procfile` | `web: gunicorn app:app` | ⚠️ Stale — references old Flask entry point (file no longer exists) |

**Result: `app.py` does not exist. The `Procfile` references it but is itself unused.**

---

## `templates/` References

Search: `templates/`, `render_template`, `Jinja2`

| Location | Status |
|----------|--------|
| `templates/` directory | ✅ Does not exist |
| `backend/app/` | ✅ No template references |
| `frontend/src/` | ✅ No template references |
| Documentation files | Referenced only in historical reports |

**Result: No Jinja2 templates exist. All UI is served by React.**

---

## `static/` References

Search: `static/`, `send_static_file`, `url_for('static'`

| Location | Status |
|----------|--------|
| `static/` directory | ✅ Does not exist |
| `backend/app/` | Only `/uploads/` mounted (for local file serving) | ✅ Correct |
| `frontend/src/` | ✅ No Flask static references |

**Result: No Flask static directory. Vite serves frontend assets.**

---

## Unused Legacy Code

| File | Status | Notes |
|------|--------|-------|
| `app.py` (root) | ✅ Removed | Flask app |
| `main.py` (root) | ✅ Removed | Flask gunicorn entry |
| `models.py` (root) | ✅ Removed | Flask SQLAlchemy models |
| `init_db.py` (root) | ✅ Removed | Flask DB init |
| `templates/` (root) | ✅ Removed | 15 Jinja2 templates |
| `static/` (root) | ✅ Removed | CSS + JS assets |
| `requirements.txt` (root) | ✅ Removed | Flask dependency list |
| `data.json` | ⚠️ Present | Original JSON data store, no longer read by any code |
| `Procfile` | ⚠️ Present | References non-existent `app:app`, not used by current deployment |
| Root `Dockerfile` | ⚠️ Fixed | Was legacy Flask/gunicorn — replaced in this audit |

---

## Hardcoded Secrets Check

Search: any API key, password, token, or connection string in source files

| File | Finding | Status |
|------|---------|--------|
| `backend/app/config.py` | `_INSECURE_DEFAULT_SECRET = "change-this-..."` | ✅ Safe — used only as a sentinel value to trigger a warning/error |
| `backend/seed.py` | `ADMIN_PASSWORD = "admin123"` | ⚠️ Default credentials — must be changed via `change_admin_password.py` before production |
| `backend/migrate_41.py` | `target_email = "hungrylearner786@gmail.com"` | ⚠️ Personal email hardcoded — one-time migration file, run once then disregard |
| `.replit` | `JWT_SECRET_KEY = "tn-board-replit-secret-2024-secure-key-xyz789"` | ⚠️ Development key in Replit env config — rotate before production |
| `frontend/src/services/admin.js` | Axios base URL is relative (`/api/v1/`) | ✅ Safe — no hardcoded domains |
| All other source files | No secrets found | ✅ Clean |

---

## Local Upload Assumptions

Search: `UPLOAD_DIR`, `/uploads/`, `os.path.join`, `local` storage

| File | Finding | Status |
|------|---------|--------|
| `backend/app/config.py` | `UPLOAD_DIR` derived from file path — creates `uploads/` at project root | ✅ Correct for local dev |
| `backend/app/services/storage.py` | `LocalStorageProvider` — stores files in `UPLOAD_DIR` | ✅ Has explicit warning about ephemeral nature in prod |
| `backend/app/main.py` | Mounts `/uploads` as static directory | ✅ Only active when using local storage |
| Documentation | Multiple warnings about local storage being ephemeral in prod | ✅ Well documented |

**Result: Local upload assumption is intentional for development. Production users are guided to use Supabase storage.**

---

## `pyproject.toml` Legacy Dependencies

| Package | Used? | Action Taken |
|---------|-------|-------------|
| `flask` | ❌ No | ✅ Removed in this audit |
| `flask-sqlalchemy` | ❌ No | ✅ Removed in this audit |
| `email_validator` | ❌ No | ✅ Removed in this audit |
| `matplotlib` | ❌ No | ✅ Removed in this audit |
| `numpy` | ❌ No | ✅ Removed in this audit |
| `openai` | ❌ No | ✅ Removed in this audit |
| `pillow` | ❌ No | ✅ Removed in this audit |
| `gunicorn` | Dev runner only | ✅ Kept (used by root Dockerfile) |
| `psycopg2-binary` | ✅ Yes | ✅ Kept |
| `python-dotenv` | ✅ Yes | ✅ Kept |
| `sqlalchemy` | ✅ Yes | ✅ Kept |
| `werkzeug` | ✅ Yes | ✅ Kept |

---

## Summary

| Category | Issues Found | Resolved |
|----------|-------------|---------|
| Flask imports in active code | 0 | N/A |
| Legacy files still present | 3 (data.json, Procfile, archive/) | Documented |
| Hardcoded secrets | 1 dev password, 1 email, 1 dev JWT | Documented, not blocking |
| Unused `pyproject.toml` deps | 7 packages | ✅ Removed |
| Root Dockerfile (legacy) | 1 | ✅ Replaced |
| Missing gitignore entries | 3 | ✅ Added |

**The active codebase is clean. All Flask code has been successfully removed.**
