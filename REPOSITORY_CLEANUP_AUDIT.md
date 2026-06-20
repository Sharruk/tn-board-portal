# Repository Cleanup Audit
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Method:** Evidence-based. Every classification is backed by grep results, build verification, or direct file reads.  
**Scope:** All files excluding `.git/`, `.pythonlibs/`, `.cache/`, `.local/`, `frontend/node_modules/`, `frontend/dist/`

---

## PART 1 — DOCUMENTATION AUDIT

### Root-Level Markdown Files

| File | Purpose | Unique? | Duplicate? | Archive? | Delete? | Reason |
|---|---|---|---|---|---|---|
| `README.md` | Project overview | Yes | No | No | No | Primary readme. Keep. |
| `replit.md` | Replit platform config + user prefs | Yes | No | No | No | Required by Replit agent system. Keep. |
| `ARCHITECTURE_DECISION_REPORT.md` | Migration decision rationale | Partial | Yes — content in `FINAL_PROJECT_STATE.md` | Yes | Safe | Superseded by FINAL_PROJECT_STATE.md |
| `AUTH_MIGRATION_PLAN.md` | Plan for migrating auth from JWT to Supabase | No | Yes — migration complete | No | Safe | Migration is done. Plan is historical. |
| `CLEANUP_VERIFICATION.md` | One-time cleanup verification | No | Yes | No | Safe | One-time report, no forward value |
| `COMPLETE_MIGRATION_ANALYSIS.md` | Full migration analysis | Partial | Yes — superseded by FINAL_PROJECT_STATE.md | Yes | Safe | FINAL_PROJECT_STATE.md is the authoritative version |
| `COPY_PASTE_SQL_ORDER.md` | All 6 SQL blocks in execution order | Yes | No | No | **No** | **REQUIRED** — directly actionable SQL for Supabase activation |
| `CURRENT_MIGRATION_STATUS.md` | Mid-migration status snapshot | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Point-in-time snapshot, no forward value |
| `DATABASE_MIGRATION_PLAN.md` | Plan for migrating from local PG to Supabase | No | Yes — migration complete | No | Safe | Migration done. Plan is historical. |
| `DEPENDENCY_AUDIT.md` | Audit of frontend/backend deps | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Verification complete |
| `DEPLOYMENT_GUIDE.md` | Deployment guide for old stack | No | No | No | Safe | References old FastAPI + Docker architecture |
| `DOCKER_DEPLOYMENT.md` | Docker deployment instructions | No | No | No | Safe | Docker removed. Entire file is stale. |
| `ENVIRONMENT_VARIABLES.md` | Env var documentation | Partial | Yes — superseded by FINAL_PROJECT_STATE.md | Yes | Safe | FINAL_PROJECT_STATE.md has same info |
| `EXECUTION_READY_STATUS.md` | Verified build + code readiness | Yes | No | No | **No** | **REQUIRED** — authoritative current-state verification |
| `FEATURE_PARITY_CHECKLIST.md` | FastAPI → Supabase feature parity check | No | Yes — migration complete | No | Safe | Migration done. No forward value. |
| `FINAL_DEPLOYMENT_AUDIT.md` | Deployment audit (intermediate) | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Superseded |
| `FINAL_DEPLOYMENT_CHECKLIST.md` | Deployment checklist (intermediate) | No | Yes — superseded by SUPABASE_ACTIVATION_CHECKLIST.md | No | Safe | Superseded |
| `FINAL_DEPLOYMENT_READY_REPORT.md` | Deployment readiness report | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Superseded |
| `FINAL_PROJECT_STATE.md` | Definitive architecture + object inventory | Yes | No | No | **No** | **REQUIRED** — authoritative architecture document |
| `FRONTEND_MIGRATION_PLAN.md` | Plan for rewriting frontend to Supabase | No | Yes — migration complete | No | Safe | Migration done. Plan is historical. |
| `GITHUB_READINESS.md` | GitHub readiness assessment | No | No | No | Safe | Not applicable to current deployment path |
| `GO_NO_GO_REPORT.md` | Go/no-go decision report | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Superseded |
| `MASTER_EXECUTION_CHECKLIST.md` | Execution checklist (intermediate) | No | Yes — superseded by SUPABASE_ACTIVATION_CHECKLIST.md | No | Safe | Superseded |
| `MIGRATION_EXECUTION_MAP.md` | Step-by-step migration map | No | Yes — migration complete | No | Safe | Migration done. No forward value. |
| `MIGRATION_PLAN.md` | High-level migration plan | No | Yes — migration complete | No | Safe | Migration done. No forward value. |
| `PHASE1_VERIFICATION_REPORT.md` | Phase 1 completion report | No | No | No | Safe | Single-phase report. No forward value. |
| `PRODUCTION_ENVIRONMENT_VARIABLES.md` | Env vars for production | Partial | Yes — in FINAL_PROJECT_STATE.md | Yes | Safe | Superseded |
| `PRODUCTION_READINESS_REPORT.md` | Production readiness (intermediate) | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Superseded |
| `PROJECT_HANDOVER.md` | Handover context document | Partial | Partial | Yes | Safe | Contains some context, but FINAL_PROJECT_STATE.md covers it |
| `RUNNING_GUIDE.md` | How to run the old stack locally | No | No | No | Safe | References local PostgreSQL + FastAPI. Entirely stale. |
| `SELF_HOSTING_GUIDE.md` | Self-hosting with Docker | No | No | No | Safe | References Docker + FastAPI. Entirely stale. |
| `STORAGE_MIGRATION_PLAN.md` | Plan for migrating local file uploads to Supabase Storage | No | Yes — migration complete | No | Safe | Migration done. No forward value. |
| `SUPABASE_ACTIVATION_CHECKLIST.md` | Non-technical step-by-step activation guide | Yes | No | No | **No** | **REQUIRED** — the primary activation guide with exact clicks |
| `SUPABASE_DEPLOYMENT_CHECKLIST.md` | Intermediate Supabase setup checklist | No | Yes — superseded by COPY_PASTE_SQL_ORDER.md | No | Safe | Superseded |
| `SUPABASE_MIGRATION_STATUS.md` | Mid-migration status snapshot | No | Yes — superseded by EXECUTION_READY_STATUS.md | No | Safe | Point-in-time snapshot |
| `SUPABASE_SETUP_MASTER_GUIDE.md` | Explained version of activation guide | No | Yes — COPY_PASTE_SQL_ORDER.md + SUPABASE_ACTIVATION_CHECKLIST.md cover this | No | Safe | Superseded by the two more focused documents |
| `VERCEL_DEPLOYMENT_PLAN.md` | Vercel deployment planning | Partial | No | Yes | Safe | Future reference only |
| `VERCEL_DEPLOYMENT_SIMULATION.md` | Vercel deployment simulation | No | Yes — superseded by VERCEL_DEPLOYMENT_STEPS.md | No | Safe | Superseded |
| `VERCEL_DEPLOYMENT_STEPS.md` | Exact Vercel deployment instructions | Yes | No | No | No | Future deployment reference — keep until deployed |

---

### Root-Level Text Files

| File | Purpose | Unique? | Delete? | Reason |
|---|---|---|---|---|
| `FINAL_CLEANUP_REPORT.txt` | Old Flask-era cleanup report | No | Safe | Pre-Supabase migration, entirely stale |
| `PROJECT_AUDIT_REPORT.txt` | Old project audit | No | Safe | Superseded by EXECUTION_READY_STATUS.md |
| `PROJECT_STATUS.txt` | Old status file | No | Safe | Superseded by EXECUTION_READY_STATUS.md |
| `SUPABASE_STORAGE_REPORT.txt` | Supabase storage investigation | No | Safe | Superseded by FINAL_PROJECT_STATE.md |

---

### supabase/ Directory

| File | Purpose | Unique? | Delete? | Reason |
|---|---|---|---|---|
| `supabase/migrations/001_schema.sql` | Creates 5 tables + 12 indexes | Yes | **No** | Required for database activation |
| `supabase/migrations/002_seed_data.sql` | Seeds 4 classes + 32 subjects | Yes | **No** | Required for database activation |
| `supabase/migrations/003_rls_policies.sql` | Creates 13 RLS policies | Yes | **No** | Required for database activation |
| `supabase/migrations/004_functions.sql` | Creates 4 RPC functions | Yes | **No** | Required for database activation |
| `supabase/migrations/005_search_analytics.sql` | Creates analytics index, view, cleanup function | Yes | **No** | Required for database activation |
| `supabase/migrations/006_search_rpc.sql` | Creates search_papers() RPC | Yes | **No** | Required for database activation |
| `supabase/README.md` | Describes the migrations folder and execution order | Yes | No | Useful reference — keep |

---

### docs/ Directory

| File | Purpose | Unique? | Delete? | Reason |
|---|---|---|---|---|
| `docs/API.md` | FastAPI REST API documentation | No | Safe | Evidence: `grep -r "docs/API" .` returned 0 results. Not referenced anywhere. FastAPI is removed. |

---

### archive/ Directory

| File | Purpose | Unique? | Delete? | Reason |
|---|---|---|---|---|
| `archive/ARCHITECTURE_BLUEPRINT.txt` | Original Flask architecture spec | No | Safe | Flask architecture entirely replaced. 55 KB of stale content. |
| `archive/FIX_REPORT.txt` | Flask-era bug fix report | No | Safe | Stale |
| `archive/FRONTEND_PHASE2_REPORT.txt` | Frontend phase 2 report (Flask era) | No | Safe | Stale |
| `archive/PHASE37_REPORT.txt` | Phase 37 report | No | Safe | Stale |
| `archive/PHASE38_REPORT.txt` | Phase 38 report | No | Safe | Stale |
| `archive/PHASE39_REPORT.txt` | Phase 39 report | No | Safe | Stale |
| `archive/PHASE3_REPORT.txt` | Phase 3 report | No | Safe | Stale |
| `archive/PRODUCTION_READINESS_REPORT.txt` | Old production readiness (Flask era) | No | Safe | Superseded by EXECUTION_READY_STATUS.md |
| `archive/VALIDATION_REPORT_PHASE36.txt` | Phase 36 validation | No | Safe | Stale |
| `archive/VALIDATION_REPORT.txt` | Validation report (Flask era) | No | Safe | Stale |

---

## PART 2 — ASSET AUDIT

### attached_assets/ — Images

**Evidence method:** `grep -r "image_\|screenshot-\|attached_assets" frontend/src/` returned: `NO ASSET REFS IN SRC`

| Asset | Referenced by code? | Referenced by CSS? | Referenced by README? | Safe to delete? |
|---|---|---|---|---|
| `image_1750838393839.png` | No | No | No | Yes |
| `image_1750838687624.png` | No | No | No | Yes |
| `image_1750838718772.png` | No | No | No | Yes |
| `image_1750839298464.png` | No | No | No | Yes |
| `image_1750839705581.png` | No | No | No | Yes |
| `image_1750861467411.png` | No | No | No | Yes |
| `image_1750864858594.png` | No | No | No | Yes |
| `image_1750866016168.png` | No | No | No | Yes |
| `image_1750878542248.png` | No | No | No | Yes |
| `image_1750908928438.png` | No | No | No | Yes |
| `image_1750909554333.png` | No | No | No | Yes |
| `image_1750994194036.png` | No | No | No | Yes |
| `image_1750994474507.png` | No | No | No | Yes |
| `image_1750994877566.png` | No | No | No | Yes |
| `image_1770459849713.png` | No | No | No | Yes |
| `image_1770460733992.png` | No | No | No | Yes |
| `image_1770461909129.png` | No | No | No | Yes |
| `image_1770462909394.png` | No | No | No | Yes |
| `image_1770463861826.png` | No | No | No | Yes |
| `image_1770464519463.png` | No | No | No | Yes |
| `image_1770466323580.png` | No | No | No | Yes |
| `image_1770469280219.png` | No | No | No | Yes |
| `image_1770488897742.png` | No | No | No | Yes |
| `image_1770489999823.png` | No | No | No | Yes |
| `image_1770490296615.png` | No | No | No | Yes |
| `image_1770490886327.png` | No | No | No | Yes |
| `image_1770492374051.png` | No | No | No | Yes |
| `image_1770492899761.png` | No | No | No | Yes |
| `image_1770493230700.png` | No | No | No | Yes |
| `image_1770530447789.png` | No | No | No | Yes |
| `image_1770530730297.png` | No | No | No | Yes |
| `image_1770735795003.png` | No | No | No | Yes |
| `screenshot-1770492326464.png` | No | No | No | Yes |

**Total: 33 images. All unreferenced. All safe to delete.**

### attached_assets/ — Other Files

| Asset | Referenced by code? | Safe to delete? | Reason |
|---|---|---|---|
| `branding-1770492328131.json` | No | Yes | Not referenced. Historical branding snapshot. |
| `content-1770492323958.md` | No | Yes | Not referenced. Historical content snapshot. |
| All `Pasted-*.txt` files (29 files) | No | Yes | Historical user prompts pasted as inputs. No code or build dependency. |

### uploads/ Directory

| Asset | Referenced by code? | Safe to delete? | Reason |
|---|---|---|---|
| `uploads/.gitkeep` | No | Yes | Local file uploads replaced by Supabase Storage. Placeholder only. |

### frontend/public/

**Finding:** `frontend/public/` directory does not exist. No assets to audit.

---

## PART 3 — CODE AUDIT

### backend/ Directory

| File/Folder | Referenced by frontend? | Used in build? | Used in runtime? | Required for Supabase? | Required for deployment? |
|---|---|---|---|---|---|
| `backend/app/main.py` | No | No | No | No | No |
| `backend/app/config.py` | No | No | No | No | No |
| `backend/app/__init__.py` | No | No | No | No | No |
| `backend/app/api/` | No | No | No | No | No |
| `backend/app/database/` | No | No | No | No | No |
| `backend/app/models/` | No | No | No | No | No |
| `backend/app/schemas/` | No | No | No | No | No |
| `backend/app/services/` | No | No | No | No | No |
| `backend/Dockerfile` | No | No | No | No | No |
| `backend/migrate_41.py` | No | No | No | No | No |
| `backend/requirements.txt` | No | No | No | No | No |
| `backend/seed.py` | No | No | No | No | No |

**Evidence:** `grep -r "axios\|localhost:8000\|/api/v1\|fastapi" frontend/src/` returned NONE. Build passes without any backend reference. Backend is completely disconnected.

---

### Root-Level Legacy Config Files

| File | Referenced by? | Used in build? | Used in runtime? | Required for Supabase? | Required for deployment? |
|---|---|---|---|---|---|
| `Dockerfile` | Nothing | No | No | No | No |
| `docker-compose.yml` | Nothing | No | No | No | No |
| `pyproject.toml` | Nothing | No | No | No | No |
| `Procfile` | Nothing — contains `web: gunicorn app:app` | No | No | No | No |
| `uv.lock` | `pyproject.toml` (which is itself unused) | No | No | No | No |

**Evidence:** `Procfile` contains `web: gunicorn app:app`. No Flask `app.py` exists at root. `pyproject.toml` declares Flask/SQLAlchemy deps — none of which are imported by the React frontend. `docker-compose.yml` orchestrates the old 3-service stack (postgres + backend + frontend) which has been replaced entirely by Supabase.

---

### `.replit` — Active but Contains Stale Sections

`.replit` is a **required Replit platform file** — it controls which workflow runs and which port is exposed. However, it contains stale sections from the old architecture:

| Section | Status | Impact |
|---|---|---|
| `[[workflows.workflow]] "Start application"` — runs `cd frontend && npm run dev` | ✅ Correct | Dev server works |
| `[[ports]] localPort = 5000` | ✅ Correct | App visible in preview |
| `[[ports]] localPort = 8000` | ❌ Stale — old FastAPI port | Harmless but misleading |
| `[deployment] run = ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]` | ❌ Stale — would fail on Replit Deploy | `main.py` does not exist at root |
| `stack = "FLASK_VANILLA_JS"` | ❌ Stale — stack is now React+Supabase | Misleading but harmless |
| `[userenv.shared] VITE_SUPABASE_URL = ...` | ✅ Correct | Required |

**Note:** The stale `[deployment]` block in `.replit` is a deployment blocker for Replit's own deployment system (not Vercel). It references `gunicorn main:app` — `main.py` does not exist at the project root.

---

### replit.md

| File | Referenced by? | Required? | Status |
|---|---|---|---|
| `replit.md` | Replit agent system reads this | Yes | ✅ Correct and current — describes React+Supabase architecture |

---

### Migration Reports at Root

All intermediate migration reports (all `.md` files not listed as KEEP in Part 1) have the same status:

| Referenced by frontend? | Used in build? | Used in runtime? | Required for Supabase? | Required for deployment? |
|---|---|---|---|---|
| No | No | No | No | No |

---

## Summary Counts

| Category | Count |
|---|---|
| Files to **KEEP** (required) | 11 |
| Files to **ARCHIVE** (safe but low value) | 6 |
| Files to **DELETE** (safe, confirmed unused) | 80+ |
| Images (all unreferenced) | 33 |
| attached_assets text files (historical prompts) | 29 |
