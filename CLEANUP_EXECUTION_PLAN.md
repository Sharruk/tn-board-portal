# Cleanup Execution Plan
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Status:** Audit only — nothing has been deleted or moved.  
**Instruction:** All confidence scores are evidence-based. Do not execute without review.

---

## KEEP — Do Not Touch

These files are required for the application to function, activate, or deploy.

| File/Folder | Keep Confidence | Reason |
|---|---|---|
| `frontend/` (entire directory) | 100% | The entire application. |
| `supabase/migrations/001_schema.sql` | 100% | Required to create database tables. Without it, nothing works. |
| `supabase/migrations/002_seed_data.sql` | 100% | Required to seed 4 classes and 32 subjects. Homepage shows blank without it. |
| `supabase/migrations/003_rls_policies.sql` | 100% | Required for access control. Without it, all data is either fully blocked or fully exposed. |
| `supabase/migrations/004_functions.sql` | 100% | Required for download counting, admin stats, analytics, and content status. |
| `supabase/migrations/005_search_analytics.sql` | 100% | Required for search analytics view and cleanup function. |
| `supabase/migrations/006_search_rpc.sql` | 100% | Required for the search bar. Without it, all searches fail. |
| `supabase/README.md` | 95% | Describes migration folder and execution order. |
| `COPY_PASTE_SQL_ORDER.md` | 100% | The primary activation document. Contains all 6 SQL blocks in order, ready to paste. |
| `SUPABASE_ACTIVATION_CHECKLIST.md` | 100% | Non-technical step-by-step guide with exact clicks. Required until activation is complete. |
| `FINAL_PROJECT_STATE.md` | 95% | Definitive architecture document. Complete object inventory. |
| `EXECUTION_READY_STATUS.md` | 95% | Verified build + legacy code scan. Current readiness evidence. |
| `VERCEL_DEPLOYMENT_STEPS.md` | 90% | Deployment reference. Required when deployment is initiated. |
| `README.md` | 100% | Primary project readme. |
| `replit.md` | 100% | Required by Replit platform. Read by the agent system. |
| `.replit` | 100% | Required by Replit platform. Controls workflow and port config. Do not delete. Note stale `[deployment]` block. |

---

## ARCHIVE — Safe to Move (Not Delete)

These files have some unique context that may be useful for future reference, but are no longer operationally required.

| File | Archive Confidence | Reason |
|---|---|---|
| `ARCHITECTURE_DECISION_REPORT.md` | 80% | Explains why FastAPI was dropped in favour of Supabase. Historic context. |
| `COMPLETE_MIGRATION_ANALYSIS.md` | 80% | Full before/after analysis. Unique narrative context not in FINAL_PROJECT_STATE.md. |
| `ENVIRONMENT_VARIABLES.md` | 70% | Env var documentation. Partially duplicated in FINAL_PROJECT_STATE.md. |
| `PRODUCTION_ENVIRONMENT_VARIABLES.md` | 70% | Same as above. |
| `PROJECT_HANDOVER.md` | 75% | Handover context. Some unique narrative about the migration journey. |
| `VERCEL_DEPLOYMENT_PLAN.md` | 65% | Future deployment planning. Superseded by VERCEL_DEPLOYMENT_STEPS.md but contains strategic notes. |

---

## DELETE — Evidence-Based Safe Removal

### Group A — Superseded Documentation (root-level .md)

These are intermediate or redundant documents with no unique content not already in a KEEP file.

| File | Delete Confidence | Evidence |
|---|---|---|
| `AUTH_MIGRATION_PLAN.md` | 99% | Migration complete. Plan has no forward value. Not referenced by any file. |
| `CLEANUP_VERIFICATION.md` | 99% | One-time verification snapshot. Superseded by EXECUTION_READY_STATUS.md. |
| `CURRENT_MIGRATION_STATUS.md` | 99% | Point-in-time snapshot. Superseded by EXECUTION_READY_STATUS.md. |
| `DATABASE_MIGRATION_PLAN.md` | 99% | Migration complete. Plan has no forward value. |
| `DEPENDENCY_AUDIT.md` | 99% | Superseded by EXECUTION_READY_STATUS.md legacy scan. |
| `DEPLOYMENT_GUIDE.md` | 99% | References old FastAPI + Docker stack. Entirely stale. |
| `DOCKER_DEPLOYMENT.md` | 100% | Docker removed. Entire file is stale. No Docker in current architecture. |
| `FEATURE_PARITY_CHECKLIST.md` | 99% | Migration complete. No forward value. |
| `FINAL_DEPLOYMENT_AUDIT.md` | 99% | Superseded by EXECUTION_READY_STATUS.md. |
| `FINAL_DEPLOYMENT_CHECKLIST.md` | 99% | Superseded by SUPABASE_ACTIVATION_CHECKLIST.md. |
| `FINAL_DEPLOYMENT_READY_REPORT.md` | 99% | Superseded by EXECUTION_READY_STATUS.md. |
| `FRONTEND_MIGRATION_PLAN.md` | 99% | Migration complete. No forward value. |
| `GITHUB_READINESS.md` | 99% | Not applicable to current deployment path. Not referenced. |
| `GO_NO_GO_REPORT.md` | 99% | Superseded by EXECUTION_READY_STATUS.md. |
| `MASTER_EXECUTION_CHECKLIST.md` | 99% | Superseded by SUPABASE_ACTIVATION_CHECKLIST.md. |
| `MIGRATION_EXECUTION_MAP.md` | 99% | Migration complete. No forward value. |
| `MIGRATION_PLAN.md` | 99% | Migration complete. No forward value. |
| `PHASE1_VERIFICATION_REPORT.md` | 99% | Single-phase report. No forward value. |
| `PRODUCTION_READINESS_REPORT.md` | 99% | Superseded by EXECUTION_READY_STATUS.md. |
| `RUNNING_GUIDE.md` | 100% | References local PostgreSQL + FastAPI + uvicorn. Entirely stale. |
| `SELF_HOSTING_GUIDE.md` | 100% | References Docker + FastAPI self-hosting. Entirely stale. |
| `STORAGE_MIGRATION_PLAN.md` | 99% | Migration complete. No forward value. |
| `SUPABASE_DEPLOYMENT_CHECKLIST.md` | 99% | Superseded by COPY_PASTE_SQL_ORDER.md. |
| `SUPABASE_MIGRATION_STATUS.md` | 99% | Point-in-time snapshot. Superseded by EXECUTION_READY_STATUS.md. |
| `SUPABASE_SETUP_MASTER_GUIDE.md` | 95% | Superseded by COPY_PASTE_SQL_ORDER.md + SUPABASE_ACTIVATION_CHECKLIST.md combined. |
| `VERCEL_DEPLOYMENT_SIMULATION.md` | 99% | Superseded by VERCEL_DEPLOYMENT_STEPS.md. |

---

### Group B — Root-Level Text Files

| File | Delete Confidence | Evidence |
|---|---|---|
| `FINAL_CLEANUP_REPORT.txt` | 99% | Flask-era report. Architecture entirely replaced. |
| `PROJECT_AUDIT_REPORT.txt` | 99% | Old audit. Superseded by EXECUTION_READY_STATUS.md. |
| `PROJECT_STATUS.txt` | 99% | Old status file. Superseded by EXECUTION_READY_STATUS.md. |
| `SUPABASE_STORAGE_REPORT.txt` | 99% | Investigation report. Superseded by FINAL_PROJECT_STATE.md. |

---

### Group C — docs/ Directory

| File | Delete Confidence | Evidence |
|---|---|---|
| `docs/API.md` | 100% | FastAPI REST API documentation. FastAPI removed. `grep -r "docs/API" .` = 0 results. Not referenced anywhere. |
| `docs/` (directory) | 100% | Empty after `API.md` removal. |

---

### Group D — archive/ Directory

| File | Delete Confidence | Evidence |
|---|---|---|
| `archive/ARCHITECTURE_BLUEPRINT.txt` | 100% | 55 KB spec for the old Flask architecture. Entirely superseded. |
| `archive/FIX_REPORT.txt` | 100% | Flask-era bug fix. No relation to current codebase. |
| `archive/FRONTEND_PHASE2_REPORT.txt` | 100% | Phase report from Flask era. |
| `archive/PHASE37_REPORT.txt` | 100% | Phase report. No forward value. |
| `archive/PHASE38_REPORT.txt` | 100% | Phase report. No forward value. |
| `archive/PHASE39_REPORT.txt` | 100% | Phase report. No forward value. |
| `archive/PHASE3_REPORT.txt` | 100% | Phase report. No forward value. |
| `archive/PRODUCTION_READINESS_REPORT.txt` | 100% | Flask-era. Superseded by EXECUTION_READY_STATUS.md. |
| `archive/VALIDATION_REPORT_PHASE36.txt` | 100% | Flask-era. No forward value. |
| `archive/VALIDATION_REPORT.txt` | 100% | Flask-era. No forward value. |
| `archive/` (directory) | 100% | Empty after above deletions. |

---

### Group E — backend/ Directory

| File/Folder | Delete Confidence | Evidence |
|---|---|---|
| `backend/` (entire directory) | 100% | FastAPI backend. Frontend has zero imports from it. `grep -r "localhost:8000\|/api/v1\|from.*backend" frontend/src/` = NONE. `npm run build` passes without it. Not referenced by `.replit` workflow. |

**Detail — what's inside backend/:**
- `backend/app/api/` — FastAPI route handlers
- `backend/app/config.py` — FastAPI + PostgreSQL config
- `backend/app/database/` — SQLAlchemy session management
- `backend/app/models/` — SQLAlchemy ORM models
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/services/` — Business logic layer
- `backend/app/main.py` — FastAPI app entry point
- `backend/Dockerfile` — Container image for the backend
- `backend/migrate_41.py` — One-time migration script
- `backend/requirements.txt` — FastAPI + PyJWT + uvicorn deps
- `backend/seed.py` — Old seed script (data now in 002_seed_data.sql)

---

### Group F — Root-Level Legacy Config Files

| File | Delete Confidence | Evidence |
|---|---|---|
| `Dockerfile` | 100% | Builds the FastAPI backend container. Backend removed. |
| `docker-compose.yml` | 100% | Orchestrates postgres + FastAPI backend + frontend. All replaced by Supabase. |
| `pyproject.toml` | 100% | Python deps: Flask, SQLAlchemy, gunicorn. Not used by React frontend. Not referenced by any build step. |
| `Procfile` | 100% | Contains `web: gunicorn app:app`. No Flask `app.py` exists. Not used by current workflow. |
| `uv.lock` | 100% | Python lock file. Only relevant to `pyproject.toml` which is itself safe to delete. |

---

### Group G — uploads/ Directory

| File | Delete Confidence | Evidence |
|---|---|---|
| `uploads/.gitkeep` | 95% | Placeholder for local file uploads. File storage replaced by Supabase Storage. `docker-compose.yml` mounted this as a volume — docker-compose is also being removed. |
| `uploads/` (directory) | 95% | Empty after `.gitkeep` removal. |

---

### Group H — attached_assets/ Directory

| Category | Delete Confidence | Evidence |
|---|---|---|
| All 33 PNG images | 100% | `grep -r "image_\|screenshot-\|attached_assets" frontend/src/` = NO ASSET REFS IN SRC. Build passes without them. Not referenced in any `.md`, `.jsx`, `.js`, `.css`. |
| `screenshot-1770492326464.png` | 100% | Same evidence as above. |
| `branding-1770492328131.json` | 100% | Not imported by any source file. Not referenced in any doc. |
| `content-1770492323958.md` | 99% | Not referenced by any source file or doc. Historical content snapshot. |
| All 29 `Pasted-*.txt` files | 100% | Historical user prompts copied as input files. Not referenced anywhere. No build or runtime dependency. |

---

## Stale Configuration — Not Deletable But Requires Manual Fix

These are in files that cannot be deleted (they are platform-required), but contain stale content that should be corrected at an appropriate time.

| File | Stale Content | Impact |
|---|---|---|
| `.replit` | `[deployment] run = ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]` — references `main.py` which does not exist | **Blocks Replit Deploy** — if deployed via Replit (not Vercel), this command would fail immediately |
| `.replit` | `[[ports]] localPort = 8000` — old FastAPI port | Harmless. Misleading. |
| `.replit` | `stack = "FLASK_VANILLA_JS"` | Harmless. Misleading. Stack is React + Supabase. |

---

## Impact Summary

| Action | Files affected | Disk space freed (approx) |
|---|---|---|
| Delete Group A (superseded docs) | 25 .md files | ~500 KB |
| Delete Group B (stale .txt files) | 4 files | ~50 KB |
| Delete Group C (docs/) | 2 files + dir | ~20 KB |
| Delete Group D (archive/) | 10 files + dir | ~135 KB |
| Delete Group E (backend/) | ~20 files + dir | ~50 KB |
| Delete Group F (legacy config) | 5 files | ~15 KB |
| Delete Group G (uploads/) | 1 file + dir | Negligible |
| Delete Group H (attached_assets/) | 64 files + dir | ~15 MB (images) |
| **Total** | **~131 files + 4 directories** | **~16 MB** |

No deletion in any group affects:
- `npm run build` ✅
- The Supabase migration files ✅
- The activation checklist ✅
- The running dev server ✅
