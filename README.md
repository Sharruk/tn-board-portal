# TN Board Portal

<div align="center">

**A centralized, community-driven digital education platform by Hungry Learner for Tamil Nadu State Board students (Classes 9–12).**

[![Live Site](https://img.shields.io/badge/Live%20Site-tn--board--portal.vercel.app-black?style=for-the-badge&logo=vercel)](https://tn-board-portal.vercel.app/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4.10-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Supabase](https://img.shields.io/badge/Supabase-DB%20%26%20Storage-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Firebase](https://img.shields.io/badge/Firebase-Auth-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)

### 🌐 [Visit Live Portal → tn-board-portal.vercel.app](https://tn-board-portal.vercel.app/)

</div>

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Initial Setup & Environment Configuration](#4-initial-setup--environment-configuration)
5. [Running the Application Using Docker (Recommended)](#5-running-the-application-using-docker-recommended)
6. [Backend API Service](#6-backend-api-service)
7. [Frontend Single-Page Application](#7-frontend-single-page-application)
8. [Database & Migrations](#8-database--migrations)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Centralized Administrative Audit Logging](#10-centralized-administrative-audit-logging)
11. [Transactional Storage Outbox](#11-transactional-storage-outbox)
12. [Testing & Quality Assurance](#12-testing--quality-assurance)
13. [Production Deployment Architecture](#13-production-deployment-architecture)
14. [Troubleshooting Guide](#14-troubleshooting-guide)

---

## 1. Project Overview

Tamil Nadu State Board school students (Classes 9, 10, 11, and 12) preparing for board examinations often encounter fragmented, paywalled, or low-quality study materials across unverified websites.

**TN Board Portal** is an open, independent community education platform developed by **Hungry Learner**. It provides students, educators, and parents with a fast, verified, and centralized repository of previous years' question papers, answer keys, official government circulars, syllabus updates, and video explanations — free and accessible without mandatory registration.

> **Disclaimer:** TN Board Portal is an independent community initiative developed by Hungry Learner for students of the Tamil Nadu State Board. It is not an official government agency portal.

### Key Capabilities
- 📚 **Academic Hierarchy**: Seamless navigation across Classes 9, 10, 11, and 12, categorized by subject and practical lab requirements.
- 🔍 **Full-Text Multi-Field Search**: High-performance search across titles, exam types (Annual, Half-Yearly, Quarterly, Mid-Term, Unit Tests), districts, and subjects with automatic query alias expansion (e.g., `maths` → `mathematics`).
- 📄 **Rich Paper Viewer & Direct Downloads**: In-browser PDF rendering, structured study notes, and YouTube video embeds, with approved, human-readable download filenames served via HTTP `Content-Disposition`.
- 📢 **Official Circulars & Education News**: Dedicated sections for government examination notifications and education updates.
- 🛡️ **Role-Based Admin Governance**: Multi-user administrative governance (Super Admin, Admin, Contributor) with atomic appointment claims, material review queues, and immutable audit logging.

---

## 2. System Architecture

### Conceptual Local Docker Architecture
Both services start together inside Docker Compose with automated health checks and local reverse-proxy routing:

```text
                                 Browser
                                    |
                                    | http://localhost:5000
                                    v
                             Docker Compose
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
   tn-board-frontend                               tn-board-backend
   React 18 + Vite Dev Server                      FastAPI + Uvicorn
   Port 5000 (0.0.0.0)                             Port 8000 (0.0.0.0)
            |                                               |
            +---- Reverse Proxy (/api/*, /health) --------->+
                                                            |
                             +------------------------------+------------------------------+
                             |                                                             |
                             v                                                             v
                   Supabase PostgreSQL                                            Supabase Storage
            (aws-1-ap-south-1.pooler.supabase.com:5432)                     (papers, official-updates, news-media)
                             |
                             v
                    storage_outbox
            (SELECT FOR UPDATE SKIP LOCKED)
                             |
                             v
                tn-board-outbox-worker
                   (Optional Profile)
```

### Production Vercel Architecture
In production, the platform runs as a unified monorepo on Vercel:
- **Frontend**: Pre-compiled React static assets in `frontend/dist` served by Vercel's global CDN edge.
- **Backend**: FastAPI app served via serverless Python function runtime at `/api/index.py`.
- **Routing**: `vercel.json` transparently routes `/api/(.*)`, `/docs`, `/openapi.json`, and `/health` to `/api/index.py`, and all other routes to `/index.html` for client-side React Router navigation.

---

## 3. Prerequisites

- **Docker Engine & Docker Compose**: Docker Desktop (Windows/macOS) or Docker Engine 24+ inside WSL2 (Ubuntu 22.04+).
- **Git**: Installed locally.
- **Node.js**: v20+ (only required if developing outside Docker).
- **Python**: 3.12+ (only required if developing outside Docker).
- **Accounts**:
  - Supabase account with active PostgreSQL database and Storage buckets.
  - Firebase project with Google Sign-In enabled.

---

## 4. Initial Setup & Environment Configuration

### 1. Clone the Repository
```bash
git clone https://github.com/Sharruk/tn-board-portal.git
cd tn-board-portal
```

### 2. Configure Environment Files
The project uses separated environment files to prevent backend secrets from leaking into client-side JavaScript bundles:

```bash
# 1. Backend environment file (contains database credentials and service keys)
cp backend/.env.example backend/.env

# 2. Frontend environment file (contains public Firebase and Supabase client keys)
cp frontend/.env.example frontend/.env.local
```

### Key Environment Variables

| Variable | Target File | Purpose | Security Level |
|---|:---:|---|:---:|
| `SUPABASE_DATABASE_URL` | `backend/.env` | Direct connection to PostgreSQL pooler (port 5432) | **Confidential** |
| `SUPABASE_SERVICE_ROLE_KEY` | `backend/.env` | Supabase service-role key for outbox storage deletion | **Secret** |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | `backend/.env` | Firebase Admin SDK service account key | **Secret** |
| `ADMIN_EMAIL` | `backend/.env` | Primary Super Admin Google account email | Public / Config |
| `VITE_SUPABASE_URL` | `frontend/.env.local` | Public Supabase project API URL | Public |
| `VITE_SUPABASE_ANON_KEY` | `frontend/.env.local` | Public Supabase anonymous API key (RLS-gated) | Public |
| `VITE_FIREBASE_API_KEY` | `frontend/.env.local` | Firebase Web client API key | Public |
| `VITE_API_PROXY_TARGET` | `frontend/.env.local` | In Docker, points to `http://backend:8000` | Internal Config |

---

## 5. Running the Application Using Docker (Recommended)

Start the entire full-stack platform using a single Docker Compose command:

```bash
docker compose up --build -d
```

### Verified Local Endpoints

| Service | Access URL | Description |
|---|---|---|
| **Frontend Application** | [http://localhost:5000](http://localhost:5000) | Main student & admin React portal |
| **Admin Portal** | [http://localhost:5000/admin/login](http://localhost:5000/admin/login) | Admin management & review console |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | Direct FastAPI REST service |
| **Health Check Probe** | [http://localhost:8000/health](http://localhost:8000/health) | API health check status |
| **Swagger OpenAPI Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation |

### Inspecting Running Services
```bash
# Check container status and health
docker compose ps

# Follow logs from all services in real time
docker compose logs -f

# Follow backend logs specifically
docker compose logs -f backend

# Follow frontend logs specifically
docker compose logs -f frontend
```

### Stopping and Rebuilding
```bash
# Stop all containers (preserves build cache and data)
docker compose down

# Rebuild containers after dependency or Dockerfile changes
docker compose up --build -d

# Restart a specific service without rebuilding
docker compose restart backend
```

---

## 6. Backend API Service

The backend is built with FastAPI and SQLAlchemy 2.0. It exposes all domain entities under the canonical `/api/v1` prefix.

- **Startup Command (Docker)**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`
- **Application Factory**: Located in `backend/app/main.py`.
- **Health Endpoints**:
  - `GET /health` (top-level alias for container health checks and load balancers).
  - `GET /api/v1/health` (versioned health endpoint).

### Running Backend Tests
Execute the comprehensive 298-test test suite:
```bash
# Inside WSL / Linux
cd backend
./.venv/bin/pytest tests -v

# Or directly inside the running Docker container
docker exec tn-board-backend pytest -v
```

---

## 7. Frontend Single-Page Application

The frontend is built with React 18 and Vite.

- **Development Port**: Port `5000` (configured with `host: 0.0.0.0` and `usePolling: true` for WSL file-change detection).
- **Reverse Proxy**: Vite proxies all `/api/*`, `/health`, and `/docs` requests to `http://backend:8000` inside Docker, eliminating browser CORS preflight overhead and host DNS resolution problems.
- **Production Build Command**:
  ```bash
  cd frontend
  npm run build
  ```
  Artifacts are compiled to `frontend/dist/`.

---

## 8. Database & Migrations

The database layer uses Supabase PostgreSQL accessed via SQLAlchemy with session pooling.

### Migration Directory
All database schemas and versioned SQL migrations live in `supabase/migrations/`:
- `001_initial_schema.sql` through `030_...sql`: Baseline classes, subjects, papers, and community schemas.
- `031_claim_appointment_concurrency_fix.sql`: Multi-user role appointment claim concurrency and advisory locking.
- `032_storage_outbox.sql`: Transactional storage outbox table, partial indexes, and status constraints.

### ⚠️ Production Migration Notice
> **IMPORTANT:** Migrations `031` and `032` have been fully tested and verified against local PostgreSQL 16 containers, but **have NOT yet been applied to production Supabase**.
>
> Docker startup **never** runs migrations automatically against production databases. Production migrations must be applied explicitly by an authorized administrator through the Supabase SQL Editor.
>
> **DO NOT** execute destructive commands (`DROP TABLE ... CASCADE`) in production.

---

## 9. Authentication & Authorization

Authentication is powered by Firebase Google Sign-In with server-side role verification.

### Role Hierarchy
1. **Super Admin**: Defined by `ADMIN_EMAIL` in `backend/.env`. Holds full platform governance privileges (promoting/revoking administrators, scheduling outbox workers, audit log inspection). Cannot be demoted or revoked.
2. **Admin**: Authorized via pre-authorized email or database role appointment. Can manage papers, review submissions, moderate community posts, and publish notices/news. Cannot revoke Super Admins or perform self-demotion.
3. **Contributor**: Registered user who has submitted materials.
4. **Student / Public**: Unauthenticated or authenticated student user with read and discussion access.

### Atomic Appointment Claiming
When an appointed administrator signs in for the first time with their pre-authorized email, the backend executes `claim_pending_appointment_atomic()` via PostgreSQL advisory locks. This safely converts the pending appointment into an active admin role, records role history, and emits an immutable audit log.

---

## 10. Centralized Administrative Audit Logging

All administrative operations must pass through backend services that atomically record audit logs into `admin_activity_logs`.

- **Audit Immutability**: All client-side direct inserts into `audit_logs` have been deprecated and removed. Actor identity is derived strictly on the server from the verified Firebase ID token.
- **Atomic Transaction Enlistment**: The business mutation and audit log insertion share the same SQLAlchemy database session. If the audit log fails, the entire transaction rolls back, preventing untracked administrative mutations.
- **Tracked Actions**:
  - Governance: `ADMIN_PROMOTED`, `ADMIN_REVOKED`, `ADMIN_PREAUTHORIZED`, `ADMIN_APPOINTMENT_CLAIMED`
  - Content: `PAPER_CREATED`, `PAPER_UPDATED`, `PAPER_DELETED`, `NOTICE_CREATED`, `NOTICE_UPDATED`, `NOTICE_DELETED`, `NEWS_CREATED`, `NEWS_UPDATED`, `NEWS_DELETED`
  - Submissions: `SUBMISSION_APPROVED`, `SUBMISSION_REJECTED`, `SUBMISSION_RESTORED`, `SUBMISSION_DELETED`
  - Community: `COMMENT_DELETED`, `POST_DELETED`, `COMMENT_REPORT_RESOLVED`, `PAPER_COMMENT_DELETED`

---

## 11. Transactional Storage Outbox

### The Problem Solved
PostgreSQL database transactions cannot encompass external HTTP calls to Supabase Storage. If a storage file is deleted immediately and the subsequent database commit fails, the file is lost forever. Conversely, if the database commits and the storage deletion fails due to network failure, orphaned files remain indefinitely.

### Outbox Solution
When an entity (paper, notice, news article) is deleted or updated with a new file:
1. Database mutation + audit log + `storage_outbox` task are committed **atomically** in the same transaction.
2. An asynchronous worker queries `storage_outbox` using `SELECT ... FOR UPDATE SKIP LOCKED`.
3. The worker executes the Supabase Storage deletion API call.
4. If Storage returns `404 / Not Found`, it is treated as an idempotent success.
5. If Storage fails due to network errors, the job retries with exponential backoff:
   $$t_{\text{retry}} = \min(3600\text{s}, 5\text{s} \times 2^{\text{attempt} - 1})$$
6. After 5 failed attempts, the task transitions to `DEAD_LETTER` with the full error stack trace preserved.
7. Abandoned or crashed worker leases (`leased_at` expired) are automatically reclaimed on subsequent runs.

### Outbox Worker Execution
```bash
# Run one-shot batch process (cron job):
python -m app.workers.outbox_worker --once

# Run continuous background daemon:
python -m app.workers.outbox_worker --interval 10 --batch-size 10

# Run in Docker Compose:
docker compose --profile worker up -d
```

---

## 12. Testing & Quality Assurance

### Full Test Suite Execution
```bash
# Execute backend test suite
pytest backend/tests -v
```
**Results**: **298 / 298 tests passing** (0 regressions, 0 failures):
- `test_admin_roles.py`: 39 tests (appointment claims, governance, self-demotion prevention)
- `test_submissions.py`: 116 tests (review queue, approvals, cascading deletions)
- `test_papers.py`: 43 tests (search expansion, downloads, create/update/delete)
- `test_community.py`: 32 tests (moderation, reports, comments)
- `test_admin_activity.py`: 16 tests (audit filtering, transaction rollback)
- `test_notices.py`: 7 tests (notices CRUD, audit logging, outbox queueing)
- `test_news.py`: 7 tests (news CRUD, slug uniqueness, audit logging)
- `test_outbox.py`: 8 tests (SKIP LOCKED concurrency, lease recovery, backoff)
- `test_classes.py`, `test_subjects.py`, `test_auth.py`, `test_health.py`: 30 tests

### Frontend Build Verification
```bash
npm.cmd --prefix frontend run build
```
**Results**: Clean production compilation with Vite in ~3.5s with zero syntax or bundle errors.

---

## 13. Production Deployment Architecture

In production, frontend and backend deploy as a single unified application on **Vercel**:

1. **Monorepo Structure**: Vercel detects `package.json` in `frontend` and builds the static SPA.
2. **Serverless Functions**: Vercel detects `api/index.py` and deploys the FastAPI application to AWS Lambda microVMs under Vercel's Python runtime.
3. **Database Connection Pooling**: In `backend/app/db/session.py`, the engine automatically detects Vercel (`VERCEL=1`) and sets `pool_size=2, max_overflow=1`, allowing up to 3 connections per warm instance without exhausting Supabase's connection budget.
4. **Outbox Worker in Production**: Triggered periodically (every 1 to 5 minutes) via Vercel Cron or an authenticated external webhook hitting:
   ```http
   POST /api/v1/admin/outbox/process?batch_size=20&lease_seconds=60
   Authorization: Bearer <SUPER_ADMIN_TOKEN>
   ```

---

## 14. Troubleshooting Guide

### 1. Docker Daemon Unavailable
- **Symptom**: `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`
- **Solution**: Ensure Docker Desktop is running on Windows with the WSL2 integration enabled for your distribution (**Docker Desktop Settings → Resources → WSL Integration → Enable Ubuntu**).

### 2. Port Conflict (5000 or 8000 Already in Use)
- **Symptom**: `Bind for 0.0.0.0:5000 failed: port is already allocated`
- **Solution**: Check for host processes using the ports:
  ```powershell
  # Windows PowerShell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess
  ```
  Stop lingering node or python processes, or stop previous Docker containers with `docker compose down`.

### 3. Frontend Cannot Reach Backend (`HTTP 502 Bad Gateway` on `/api/*`)
- **Symptom**: Browser network tab shows 502 or connection refused when fetching `/api/v1/...`.
- **Solution**: Verify that `backend` container is healthy (`docker compose ps`). Vite proxies `/api` to `http://backend:8000`. If backend failed to start, inspect logs with `docker compose logs backend`.

### 4. Database Connection Refused / Timeout
- **Symptom**: Backend logs report `could not connect to server: Connection refused`.
- **Solution**: Check that `SUPABASE_DATABASE_URL` in `backend/.env` is using port **5432** (Supabase Session Pooler). Direct port 6543 requires transaction mode pooler configuration.

### 5. Google Sign-In Unauthorized Domain Error
- **Symptom**: Firebase Auth popup fails with `auth/unauthorized-domain`.
- **Solution**: In the **Firebase Console → Authentication → Settings → Authorized Domains**, ensure `localhost` is listed.

### 6. WSL File-Watching Not Updating React Code
- **Symptom**: Editing files in Windows does not trigger hot reload inside the container.
- **Solution**: The frontend Vite server is configured with `watch: { usePolling: true }` in `frontend/vite.config.js`. Ensure you have not disabled polling.

---

<div align="center">

**Hungry Learner** — Empowering students through open digital education.

</div>
