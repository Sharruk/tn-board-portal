# Final Pre-Delete Inventory
## TN State Board Learning Platform
**Generated:** 2025-06-20 — immediately before cleanup execution  
**Baseline build:** ✅ PASS — 105 modules, dist built in 3.81s

---

## Counts (excluding .git, .cache, .pythonlibs, .local, .agents, frontend/node_modules)

| Metric | Count |
|---|---|
| Total files | 246 |
| Total directories | 47 |

---

## Root Folder Listing

```
ARCHITECTURE_DECISION_REPORT.md
archive/
attached_assets/
AUTH_MIGRATION_PLAN.md
backend/
BACKEND_REMOVAL_VERIFICATION.md
change_admin_password.py
CLEANUP_EXECUTION_PLAN.md
CLEANUP_VERIFICATION.md
COMPLETE_MIGRATION_ANALYSIS.md
COPY_PASTE_SQL_ORDER.md
CURRENT_MIGRATION_STATUS.md
DATABASE_MIGRATION_PLAN.md
data.json
DEPENDENCY_AUDIT.md
DEPLOYMENT_GUIDE.md
docker-compose.yml
DOCKER_DEPLOYMENT.md
Dockerfile
docs/
.dockerignore
.env.example
ENVIRONMENT_VARIABLES.md
EXECUTION_READY_STATUS.md
FEATURE_PARITY_CHECKLIST.md
FINAL_CLEANUP_REPORT.txt
FINAL_DEPLOYMENT_AUDIT.md
FINAL_DEPLOYMENT_CHECKLIST.md
FINAL_DEPLOYMENT_READY_REPORT.md
FINAL_PROJECT_STATE.md
frontend/
FRONTEND_MIGRATION_PLAN.md
GITHUB_READINESS.md
.gitignore
GO_NO_GO_REPORT.md
JWT_USAGE_AUDIT.md
MASTER_EXECUTION_CHECKLIST.md
MIGRATION_EXECUTION_MAP.md
MIGRATION_PLAN.md
PHASE1_VERIFICATION_REPORT.md
Procfile
PRODUCTION_ENVIRONMENT_VARIABLES.md
PRODUCTION_READINESS_REPORT.md
PROJECT_AUDIT_REPORT.txt
PROJECT_HANDOVER.md
PROJECT_STATUS.txt
pyproject.toml
README.md
.replit
replit.md
REPOSITORY_CLEANUP_AUDIT.md
RUNNING_GUIDE.md
SELF_HOSTING_GUIDE.md
STORAGE_MIGRATION_PLAN.md
supabase/
SUPABASE_ACTIVATION_CHECKLIST.md
SUPABASE_DEPLOYMENT_CHECKLIST.md
SUPABASE_MIGRATION_STATUS.md
SUPABASE_SETUP_MASTER_GUIDE.md
SUPABASE_STORAGE_REPORT.txt
uploads/
uv.lock
VERCEL_DEPLOYMENT_PLAN.md
VERCEL_DEPLOYMENT_SIMULATION.md
VERCEL_DEPLOYMENT_STEPS.md
```

---

## Planned Deletions by Stage

| Stage | Target | Files | Reason |
|---|---|---|---|
| A | `attached_assets/` | 65 files | Unreferenced prompts, images, branding — confirmed by grep |
| B | `backend/` | 39 files | Dead code — 0 frontend references, JWT audit confirmed |
| C | `Dockerfile`, `docker-compose.yml`, `Procfile`, `pyproject.toml`, `uv.lock` | 5 files | Docker/Python infra for deleted backend |
| D | `archive/` | 10 files | Flask-era historical reports |
| E | Stale docs per REPOSITORY_CLEANUP_AUDIT.md | 30+ files | Superseded migration plans and reports |

## Files Guaranteed to Survive All Stages

```
frontend/          (entire React app — never touched)
supabase/          (all 6 migrations + README)
README.md
replit.md
COPY_PASTE_SQL_ORDER.md
SUPABASE_ACTIVATION_CHECKLIST.md
VERCEL_DEPLOYMENT_STEPS.md
BACKEND_REMOVAL_VERIFICATION.md
JWT_USAGE_AUDIT.md
FINAL_PROJECT_STATE.md
EXECUTION_READY_STATUS.md
REPOSITORY_CLEANUP_AUDIT.md
FINAL_PRE_DELETE_INVENTORY.md (this file)
.gitignore
.replit
.env.example
```
