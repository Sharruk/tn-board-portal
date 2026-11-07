# TN Board Portal — Backend API

Production-ready FastAPI backend for the TN Board Portal, deployed serverlessly on Vercel alongside the Vite/React frontend, with full-stack local container execution via Docker Compose.

---

## 1. Stack & Architecture

| Layer | Technology | Description |
|---|---|---|
| **Framework** | FastAPI 0.115 | Asynchronous REST API framework |
| **Server / Runtime** | Uvicorn (local/Docker) / Vercel Serverless (prod) | HTTP server & serverless function runtime |
| **Database ORM** | SQLAlchemy 2.0 + psycopg2-binary | Direct PostgreSQL data access via connection pooler |
| **Database & Storage** | Supabase PostgreSQL + Supabase Storage | Managed cloud database & asset storage buckets |
| **Authentication** | Firebase Admin SDK | Google Sign-In verification & role claims |
| **Transactional Outbox** | PostgreSQL `storage_outbox` table | Durable asynchronous storage side-effect queue |
| **Config** | pydantic-settings | Strictly typed environment configuration |

```
HTTP Request
  │
  ▼
FastAPI Router (app/api/v1/endpoints/)
  │  Input validation & authentication dependencies
  ▼
Service Layer (app/services/)
  │  Business logic, atomic audit logging, & outbox queueing
  ▼
Repository Layer (app/repositories/)
  │  SQLAlchemy parameterized SQL & connection pooling
  ▼
Supabase PostgreSQL / Supabase Storage
```

---

## 2. Local Execution

### Option A: Full-Stack Docker Compose (Recommended)
From the repository root, start both frontend and backend together:
```bash
docker compose up --build -d
```
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend**: [http://localhost:5000](http://localhost:5000)

### Option B: Standalone Local Virtualenv
```bash
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Start development server with hot-reload
uvicorn app.main:app --reload --port 8000
```

---

## 3. Transactional Outbox Background Worker

When entities with attached storage files (question papers, official notices, educational news) are deleted or updated, file removals are enqueued in `storage_outbox` inside the exact same database transaction.

### Running the Worker Daemon:
```bash
# Continuous polling loop (10-second interval):
python -m app.workers.outbox_worker --interval 10 --batch-size 10

# Single batch run (for cron jobs or testing):
python -m app.workers.outbox_worker --once

# In Docker Compose (using the worker profile):
docker compose --profile worker up -d
```

### Manual Trigger via API:
Super Admins can trigger immediate outbox processing via HTTP:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/outbox/process?batch_size=10" \
  -H "Authorization: Bearer <SUPER_ADMIN_JWT>"
```

---

## 4. Backend-Mediated Storage Architecture

The backend serves as the authoritative orchestrator for all file uploads to Supabase Storage:
- **Authentication:** Firebase Authentication Bearer token (`require_admin`).
- **Authorization:** Verified server-side; client-side direct writes to Supabase Storage are completely disabled.
- **Storage Client:** `get_storage_client()` utilizes `SUPABASE_SERVICE_ROLE_KEY` to securely bypass storage RLS on the server.
- **Bucket Mapping:**
  - `papers`: Question Papers and Answer Keys (PDF only, max 50 MB)
  - `official-updates`: Official Notices and Circulars (PDF, images, Office docs, max 50 MB)
  - `news-media`: Educational News thumbnails and PDF attachments (max 20 MB)
  - `submissions`: Private student/educator submissions (max 25 MB)
- **Validation & Cleanup:** Strict extension, size, and content validation; database failures trigger immediate compensating file deletion in Supabase Storage.

---

## 5. Testing & Verification

The backend includes a comprehensive 315-test test suite covering role governance, submission workflows, community moderation, centralized audit logging, server-side storage uploads, and outbox concurrency:

```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_storage_uploads.py -v
pytest tests/test_admin_roles.py -v
pytest tests/test_submissions.py -v
pytest tests/test_notices.py -v
pytest tests/test_news.py -v
pytest tests/test_outbox.py -v
```

---

## 6. API Endpoints Reference

| Domain | Method | Path | Access | Description |
|---|---|---|:---:|---|
| **Meta** | `GET` | `/` | Public | API metadata and documentation links |
| **Health** | `GET` | `/health`, `/api/v1/health` | Public | Application health check probe |
| **Classes** | `GET` | `/api/v1/classes` | Public | List Classes 9, 10, 11, 12 |
| **Subjects** | `GET` | `/api/v1/subjects` | Public | List subjects by class |
| **Papers** | `GET` | `/api/v1/papers` | Public | List recent/popular published papers |
| **Papers** | `GET` | `/api/v1/papers/search` | Public | Multi-field search with alias expansion |
| **Papers** | `POST` | `/api/v1/papers` | Admin | Create paper with file upload & audit log |
| **Papers** | `PATCH`| `/api/v1/papers/{id}` | Admin | Update paper metadata and outbox storage |
| **Papers** | `DELETE`|`/api/v1/papers/{id}` | Admin | Delete paper, audit log, & queue outbox file |
| **Notices**| `GET` | `/api/v1/notices` | Public | Browse official government circulars |
| **Notices**| `POST` | `/api/v1/notices` | Admin | Create official notice with file upload & audit log |
| **Notices**| `PATCH`| `/api/v1/notices/{id}` | Admin | Update notice with audit log |
| **Notices**| `DELETE`|`/api/v1/notices/{id}` | Admin | Delete notice, audit log, & queue outbox file |
| **News** | `GET` | `/api/v1/news` | Public | Browse education news updates |
| **News** | `POST` | `/api/v1/news` | Admin | Create article with file upload & audit log |
| **News** | `POST` | `/api/v1/news/upload` | Admin | Upload news media (thumbnail / PDF) |
| **News** | `DELETE`|`/api/v1/news/media` | Admin | Delete media file from news-media bucket |
| **News** | `PATCH`| `/api/v1/news/{id}` | Admin | Update article with audit log |
| **News** | `DELETE`|`/api/v1/news/{id}` | Admin | Delete article, audit log, & queue outbox file |
| **Outbox** | `POST` | `/api/v1/admin/outbox/process` | Super Admin | Process claimed outbox batch |
| **Outbox** | `GET` | `/api/v1/admin/outbox/status` | Admin | Inspect queue status and failed tasks |
| **Roles** | `POST` | `/api/v1/admin/roles/claim-appointment` | Admin | Atomic appointment claiming via RPC |
| **Audit** | `GET` | `/api/v1/admin/activity-logs` | Admin | Centralized audit log inspection |
