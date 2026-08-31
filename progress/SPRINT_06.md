# Sprint 06: Vercel Full-Stack Migration & Submission Approval Stabilization

## Goal
Deploy the unified full-stack TN Board Portal application (React/Vite frontend + FastAPI serverless backend) to Vercel with Supabase PostgreSQL/Storage and Firebase Authentication. Fix the production submission approval database error, implement complete paper publishing workflow, and establish Docker local backend testing.

## Current Production Tech Stack

| Component | Technology | Hosting / Platform |
|---|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS | Vercel (Static / SPA) |
| Backend | FastAPI 0.115, Python 3.12, Uvicorn | Vercel Serverless Functions (`api/index.py`) |
| Database | PostgreSQL 15, Supabase Migrations (001–025) | Supabase Managed Database |
| File Storage | Supabase Storage (`papers`, `submissions` buckets) | Supabase Object Storage |
| Authentication | Firebase Auth (Google Sign-In, ID Token Verification) | Google Firebase Authentication |
| Local Testing | Docker (`python:3.12-slim`), pytest | Docker Desktop / local CLI |

---

## Tasks & Accomplishments

### 1. Vercel Serverless FastAPI Routing
- Configured unified same-origin routing (`/api/v1/...`) in `vercel.json` and `frontend/src/lib/api.js`.
- Decommissioned and removed all active dependencies on Render.

### 2. Submission Approval Database Fix & Enhancements
- **Problem**: Admin approval failed with `(psycopg2.errors.UndefinedColumn) column "status" of relation "papers" does not exist`.
- **Solution**:
  - Created migration `supabase/migrations/025_paper_description_and_fields.sql` adding `description`, safe `status` with check constraint, `submission_id`, `contributor_name`, and indexes.
  - Implemented resilient fallback queries in `SubmissionsRepository` and `PapersRepository` so unmigrated database columns are handled gracefully without runtime exceptions.
  - Added full admin approval support for:
    1. **Paper Title** (human-readable public title).
    2. **Download File Name** (clean file name delivered via `Content-Disposition` on download).
    3. **Description** (paper summary displayed on the public Paper Detail page).
    4. **YouTube URL** (validated and embedded on Paper Detail page).
    5. **Contributor Attribution** (`Contributed by: <Name>` with strict email privacy).
  - Added proxy download endpoint `GET /api/v1/papers/{id}/download`.

### 3. Firebase Authentication Verification
- Verified that Firebase code in `frontend/src/lib/firebase.js`, `frontend/src/contexts/AuthContext.jsx`, `frontend/src/pages/admin/LoginPage.jsx`, and backend `backend/app/dependencies/auth.py` is identical to `main`.
- Documented Vercel Preview environment variable configuration (`VITE_FIREBASE_*`) and Firebase Console Authorized Domains.

### 4. Docker Backend Testing
- Standardized `backend/Dockerfile` using `python:3.12-slim` for non-root local backend execution (`uvicorn app.main:app`).
- Verified local test command:
  ```bash
  docker build -t tn-board-backend ./backend
  docker run --env-file ./backend/.env -p 8000:8000 tn-board-backend
  ```

---

## Test Verification Results
- **Backend Test Suite**: `python -m pytest` -> **119 passed, 0 failed**.
- **Frontend Production Build**: `npm.cmd run build` -> **Built successfully** in 14.10s.
