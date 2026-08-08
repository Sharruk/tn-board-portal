# Sprint 05A: FastAPI Render Staging Deployment

## Goal
Prepare the FastAPI backend for deployment to Render and verify the complete backend stack in a real staging environment.

## Audit & Verification Tasks Completed

### 1. Render Blueprint (`render.yaml`)
- Validated `render.yaml`. The configuration correctly targets Docker, uses the `free` plan for staging, sets the branch to `dev`, and utilizes `healthCheckPath: /health`.
- Environment variable keys are correctly defined with `sync: false` for secrets, preventing sensitive data exposure in source control.

### 2. Docker Configuration (`Dockerfile`)
- Verified the `Dockerfile` uses `python:3.12-slim` AS base.
- Confirmed dependencies are installed from `requirements.txt`.
- Validated that the container runs as a non-root user (`appuser` with UID 1001).
- Confirmed the application starts correctly with `uvicorn app.main:app`.

### 3. Environment Variables (`.env.example`)
- Verified `backend/.env.example` documents all required environment variables (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `CORS_ORIGINS`).
- Checked that NO real secrets are in the repository.

### 4. Configuration (`settings.py`)
- Verified that `backend/app/config/settings.py` enforces `SUPABASE_URL` and `SUPABASE_ANON_KEY` as required variables, ensuring no credentials are hardcoded and production values can be seamlessly injected by Render.

### 5. CORS Configuration
- Reviewed `CORS_ORIGINS` in `app/main.py`. The setup correctly supports local frontend development environments and the existing Vercel production frontend `https://tn-board-portal.vercel.app` without overly permissive `*` wildcards.

### 6. Dependency Strategy
- Confirmed that `pytest` is NOT included in the production `requirements.txt`.
- Created `backend/requirements-dev.txt` for development/testing dependencies (`pytest`, `pytest-asyncio`) to ensure production images remain minimal.

### 7. Endpoints & Health Check
- Health check endpoints (`/health`, `/api/v1/health`) were confirmed accessible.
- Verified that all previously migrated endpoints (`classes`, `subjects`, `papers`, `papers/search`, `papers/download`) are correctly registered without route collisions.

## Test Results
- Ran the complete backend test suite using `python -m pytest -q backend/tests` to verify application integrity.
- **Result**: `45 passed`.

## Issues Found & Fixed
- Missing structured development requirements: Added `backend/requirements-dev.txt` for explicitly managing `pytest` and `pytest-asyncio` independently from the production Docker dependencies.
