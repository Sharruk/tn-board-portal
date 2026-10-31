# TN Board Portal

<div align="center">

**A centralized digital education platform by Hungry Learner for Tamil Nadu State Board students (Classes 9–12).**

[![Live Site](https://img.shields.io/badge/Live%20Site-tn--board--portal.vercel.app-black?style=for-the-badge&logo=vercel)](https://tn-board-portal.vercel.app/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4.10-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Supabase](https://img.shields.io/badge/Supabase-DB%20%26%20Storage-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Firebase](https://img.shields.io/badge/Firebase-Auth-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com)

### 🌐 [Visit Live Portal → tn-board-portal.vercel.app](https://tn-board-portal.vercel.app/)

</div>

---

## 📑 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [Community Contributions & Recognition](#-community-contributions--recognition)
- [Admin Material Submission Deletion](#-admin-material-submission-deletion)
- [Technology Stack](#-technology-stack)
- [System Architecture](#-system-architecture)
- [Project Structure](#-project-structure)
- [Authentication & Security](#-authentication--security)
- [Database & Storage](#-database--storage)
- [Environment Variables](#-environment-variables)
- [Local Development Setup](#-local-development-setup)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Deployment Architecture](#-deployment-architecture)
- [Development Workflow](#-development-workflow)
- [Current Status](#-current-status)
- [Roadmap](#-roadmap)
- [Hungry Learner](#-hungry-learner)
- [Contributing](#-contributing)

---

## 📖 About the Project

Tamil Nadu State Board school students (Classes 9, 10, 11, and 12) preparing for examinations often encounter fragmented, incomplete, or unverified educational materials across unofficial groups and paywalled websites.

**TN Board Portal** is an independent, community-driven education platform built by **Hungry Learner** for Tamil Nadu State Board students. It provides students, educators, and parents with a fast, verified, and centralized repository of previous years' question papers, answer keys, official government circulars, syllabus updates, and video explanations — completely free and accessible without mandatory login.

> **Disclaimer:** TN Board Portal is an independent community initiative developed by Hungry Learner for students of the Tamil Nadu State Board. It is not an official government agency portal.

---

## ✨ Key Features

### 🎓 Public Student Platform
- 📚 **Class & Subject Hierarchy**: Clean navigation across Classes 9, 10, 11, and 12 with subject classification and lab/practical indicators.
- 🔍 **Full-Text Multi-Field Search**: Fast search across titles, exam types (Annual, Half-Yearly, Quarterly, Mid-Term, Unit Tests), districts, and subjects with automatic term expansion (e.g., `maths` → `mathematics`).
- 📄 **Rich Paper Detail View**: Embedded PDF viewer, structured academic metadata, approved study notes, and responsive YouTube video explanation embeds.
- ⬇️ **Direct File Downloads**: Downloads served via high-performance CDN with human-readable, approved filenames (e.g., `Class10_Science_FirstMidTerm_July_2026_Chennai_QP.pdf`) via HTTP `Content-Disposition`.
- 💬 **Paper Discussions & Likes**: Threaded discussion comments, replies, and like counters on individual paper pages.
- 📢 **Official Notices & Circulars**: Dedicated section for official examination circulars, timetables, and government notifications with download tracking and archived notice history.
- 📰 **Educational News**: Curated Tamil Nadu education news and exam announcements.
- 🙋 **Missing Material Requests**: Community paper request board where students can request specific missing question papers.

### 🛡️ Admin Management & Review Portal
- 🔐 **Administrator Authentication**: Secure administrator login via Google Sign-In with server-side authorization against configured administrator credentials.
- 📋 **Submissions Review Workflow**: Queue of pending materials submitted by students and teachers with in-browser preview, approval configuration (custom title, clean download filename, description, YouTube URL, academic metadata), and rejection with feedback.
- 🗑️ **Safe Submission Deletion**: Permanently delete pending, rejected, and **approved/published** submissions with complete cascading cleanup of private files, linked published papers, public CDN files, and audit logging.
- 🗂 **Paper Lifecycle Management**: Upload new papers, edit academic metadata, toggle draft/published status, and execute **permanent deletions** with complete Supabase Storage object cleanup.
- 📦 **Bulk Upload Tool**: Upload batches of PDF files simultaneously with automated metadata parsing from standard file naming conventions.
- 📊 **Analytics & Audit Logging**: Real-time admin statistics, search query tracking, and immutable audit logs capturing admin upload, edit, and deletion history.

---

## 🤝 Community Contributions & Recognition

The platform uses a collaborative, admin-reviewed contribution model where students, teachers, and educators can submit educational materials for review before publication.

```mermaid
sequenceDiagram
    autonumber
    actor Contributor as Contributor (Student / Teacher)
    participant Auth as Firebase Auth
    participant Frontend as React Frontend (Vercel)
    participant Backend as FastAPI Backend (Vercel)
    participant Storage as Private Storage Bucket
    actor Admin as Platform Admin
    participant PublicStorage as Public Storage CDN
    participant Feed as Public Student Portal

    Contributor->>Auth: Sign in with Google
    Contributor->>Frontend: Fill submission form & attach files
    Frontend->>Backend: POST /api/v1/submissions (multipart) with Firebase Token
    Backend->>Backend: Verify token & record submission
    Backend->>Storage: Store file in private submissions bucket
    Admin->>Frontend: Open Admin Review Queue
    Frontend->>Backend: GET /api/v1/submissions (admin authorized)
    Admin->>Backend: Approve & set title, download filename, notes, video
    Backend->>PublicStorage: Copy file to public papers bucket (UUID key)
    Backend->>Backend: Insert paper row (status = 'published')
    Backend->>Feed: Publish to Class & Subject listings & Search
    Feed-->>Contributor: Attribution on Paper & Contributor Leaderboard
```

### Contributor Recognition & Leaderboard
- **Public Attribution**: Approved papers credit the contributor by display name (`Contributed by: <Name>`), while strictly preserving contributor email privacy.
- **My Contributions Dashboard**: Contributors can track the status of all submitted materials (Under Review, Published, or Rejected with reason) and view their published papers.
- **Positive Recognition Leaderboard**: Public leaderboard celebrating educators and students who contribute approved materials, showcasing:
  - 🏆 **Top Contributor** ($\ge 15$ approved materials or Top 3 ranking)
  - 🌟 **Active Contributor** ($\ge 5$ approved materials)
  - 🎓 **Contributor** ($\ge 1$ approved material)
  - 📈 Total downloads generated across contributed materials.
- **Dynamic Calculation**: Leaderboard statistics compute dynamically from live database records, ensuring published counts update immediately if a submission or paper is removed.

---

## 🗑️ Admin Material Submission Deletion

Administrators can permanently delete material submissions directly from the Admin Submissions portal, including submissions that have already been **approved and published**.

```
Admin Submissions Portal
  │
  ▼
Admin clicks "Delete Submission"
  │
  ▼
Confirmation Modal displays contributor metadata & cascading cleanup warning
  │
  ▼ Admin clicks "Delete Permanently"
FastAPI DELETE /api/v1/submissions/{submission_id} (Server-side admin authorization)
  │
  ├─► 1. Query Linked Published Papers (SELECT id FROM papers WHERE submission_id = :id)
  │      • Remove public storage objects from 'papers' bucket
  │      • Delete paper records from 'papers' table (cascading likes/comments)
  │      • Record paper deletion audit log
  │
  ├─► 2. Query Attached Submission Files (SELECT storage_path FROM submission_files)
  │      • Remove private files from 'submissions' bucket
  │
  ├─► 3. Delete Database Records:
  │      • DELETE FROM submission_files
  │      • DELETE FROM submissions
  │
  ├─► 4. Record Audit Log:
  │      • INSERT INTO audit_logs (action='delete_submission', target_details={...})
  │
  ▼
200 OK — Modals close, submissions list refreshes, and success toast displays
```

### Safety Model & Guarantees
- **Server-Side Authorization**: Protected with FastAPI's `require_admin` dependency; only authorized administrator accounts can execute deletion.
- **Scoped Database Paths**: Storage deletion paths are queried directly from trusted database rows (`submission_files.storage_path` and `papers.file_path`), preventing arbitrary path manipulation.
- **Resilient File Handling**: If a storage object is already missing on the storage provider, the error is logged and database cleanup proceeds smoothly without blocking the admin.
- **Immediate Catalog Removal**: Deleting an approved submission immediately removes the associated paper from public catalog feeds, search indices, subject pages, and download endpoints.
- **Administrative Auditability**: A `delete_submission` audit log entry is saved with administrator identity, timestamp, and deleted metadata.

---

## 🛠️ Technology Stack

### Frontend
| Component | Technology | Description |
|---|---|---|
| **UI Framework** | React `18.3.1` | Component-driven single-page application |
| **Build Tool** | Vite `5.4.10` | Fast development server and optimized production bundling |
| **Styling** | Tailwind CSS `3.4.14` | Utility-first, responsive design system |
| **Routing** | React Router DOM `6.27.0` | Client-side routing with protected admin layouts |
| **Authentication Client** | Firebase JS SDK `12.17.1` | Client-side Google Sign-In authentication |
| **Database Client** | `@supabase/supabase-js` `^2.108.2` | Client-side queries for public notices, news, and search RPCs |
| **API Client** | Native `fetch` + `apiFetch` | Centralized REST client with Bearer token injection for papers, submissions, and admin actions |

### Backend API
| Component | Technology | Description |
|---|---|---|
| **API Framework** | FastAPI `0.115.0` | Asynchronous Python Web API with automatic OpenAPI documentation |
| **Server Runtime** | Uvicorn `0.30.6` | ASGI web server |
| **Language** | Python `3.10` / `3.12` | Modern typed Python runtime |
| **Data Access** | SQLAlchemy `2.0.35` | Parameterized SQL queries and database connection management |
| **Configuration** | Pydantic Settings `2.4.0` | Type-safe environment variable parsing |
| **Validation** | Pydantic v2 | Strict request validation and response serialization |
| **Auth Verification** | `google-auth` `>= 2.28.0` | Server-side Firebase ID token verification |
| **HTTP Client** | HTTPX `0.27.2` | Asynchronous HTTP client for proxy downloads |

### Infrastructure & Hosting
| Component | Platform | Description |
|---|---|---|
| **Frontend Hosting** | Vercel | Global CDN hosting for React SPA with client-side routing rewrites |
| **Backend Hosting** | Vercel | Serverless Python runtime hosting for FastAPI REST API |
| **Database** | Supabase PostgreSQL | Managed PostgreSQL 15 with version-controlled migrations |
| **File Storage** | Supabase Storage | `papers` (public CDN), `submissions` (private), `official-updates`, `news-media` |
| **Authentication** | Firebase Authentication | Google OAuth2 identity provider |
| **Automated Testing** | Pytest | Test suite with 141 unit and integration tests |

---

## 🏗️ System Architecture

TN Board Portal follows a modern, cloud-native architecture with a clear separation of concerns between frontend, backend, database, storage, and authentication.

```mermaid
graph TD
    Browser["Student / Admin Browser"]
    FirebaseAuth["Firebase Authentication"]
    
    subgraph VercelPlatform ["Vercel Cloud Platform"]
        Frontend["React + Vite Frontend"]
        FastAPI["FastAPI Backend (api/index.py)"]
        
        subgraph BackendLayers ["Backend Architecture"]
            Routes["Route Endpoints (/api/v1/...)"]
            Services["Service Layer (Business Logic)"]
            Repos["Repository Layer (Data Access)"]
            AuthVerify["Token Verification (Google OAuth2 / Firebase)"]
            
            Routes --> Services
            Services --> Repos
            Routes --> AuthVerify
        end
        
        FastAPI --> Routes
    end

    Browser --> Frontend
    Browser --> FirebaseAuth
    Frontend --> FastAPI
    FirebaseAuth -.-> AuthVerify
    
    subgraph SupabasePlatform ["Supabase Platform"]
        PostgresDB[("Supabase PostgreSQL")]
        Storage[("Supabase Storage (CDN & Buckets)")]
    end

    Repos --> PostgresDB
    Repos --> Storage
```

### Key Points
- **Frontend (React SPA)** hosted on Vercel.
- **Backend (FastAPI)** deployed as serverless functions on Vercel (`api/index.py`).
- **Database** on Supabase PostgreSQL (Port 5432).
- **File storage** on Supabase Storage.
- **Authentication** via Firebase (Google Sign-In) with ID token verification in backend.
- **Clear separation of concerns** for scalability, security, and maintainability.

### Backend Layer Responsibilities
1. **Route Layer (`app/api/v1/endpoints/`)**: Defines HTTP routes, applies dependency injection (`get_db`, `require_admin`), and maps request/response schemas.
2. **Service Layer (`app/services/`)**: Implements core business logic, input validation, term expansion, and workflow orchestration.
3. **Repository Layer (`app/repositories/`)**: Manages SQL transactions, query execution, and Supabase Storage operations.
4. **Schema Layer (`app/schemas/`)**: Declares Pydantic data contracts ensuring type safety and privacy protection.

---

## 📁 Project Structure

```
tn-board-portal/
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── api/v1/                  # Route endpoints
│   │   │   ├── endpoints/           # Domain endpoints (papers, submissions, community, etc.)
│   │   │   └── router.py            # Main API v1 router
│   │   ├── config/                  # Settings and environment configuration
│   │   ├── db/                      # Database session and storage client singletons
│   │   ├── dependencies/            # FastAPI dependencies (auth, database)
│   │   ├── models/                  # Database entity representations
│   │   ├── repositories/            # Direct PostgreSQL & storage data access
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── services/                # Business logic and domain rules
│   │   ├── utils/                   # Exceptions, helpers, and constants
│   │   └── main.py                  # FastAPI app factory
│   ├── tests/                       # Automated test suite (141 tests)
│   └── requirements.txt             # Backend Python dependencies
├── frontend/                        # React SPA (Hosted on Vercel)
│   ├── public/                      # Static assets and icons
│   ├── src/
│   │   ├── components/              # UI components (navbar, footer, modals, admin shell)
│   │   ├── contexts/                # React context providers (AuthContext)
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── layouts/                 # Layout wrappers
│   │   ├── lib/                     # API client, Supabase, and Firebase initialization
│   │   ├── pages/                   # Public page views (Class, Subject, Detail, Community, etc.)
│   │   │   └── admin/               # Admin pages (Dashboard, Papers, Submissions, Notices, News)
│   │   ├── router/                  # React Router configuration
│   │   ├── services/                # Frontend API interaction services
│   │   ├── utils/                   # Download and format utilities
│   │   ├── App.jsx                  # Root React component
│   │   └── main.jsx                 # Client entry point
│   ├── package.json                 # Frontend dependencies and scripts
│   ├── tailwind.config.js           # Tailwind CSS theme configuration
│   └── vite.config.js               # Vite build and development proxy settings
├── supabase/
│   ├── migrations/                  # Ordered, forward-only SQL migrations
│   └── README.md                    # Database documentation
├── .ai/                             # Engineering guidelines and architectural standards
├── docs/                            # Deep-dive architecture documents
├── package.json                     # Monorepo build script
└── vercel.json                      # Vercel SPA routing configuration
```

---

## 🔒 Authentication & Multi-User Role Management

The platform enforces a comprehensive four-tier Role-Based Access Control (RBAC) architecture:

```
                           ┌────────────────────────────────────────┐
                           │      SUPER_ADMIN (Root Governance)     │
                           │    hungrylearner786@gmail.com (Pinned) │
                           └───────────────────┬────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
         Method 1: Direct Promotion                      Method 2: Pre-Authorization
         Promote registered USER/CONTRIBUTOR             Pre-authorize Google email invitation
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               ▼
                                  ┌─────────────────────────┐
                                  │   ADMIN (Management)    │
                                  │ Review, Moderate, Papers│
                                  └────────────┬────────────┘
                                               │ (On Revocation)
                                               ▼
                                 Restores original previous_role
                                       ┌───────┴───────┐
                                       ▼               ▼
                               ┌──────────────┐ ┌──────────────┐
                               │ CONTRIBUTOR  │ │     USER     │
                               │(Earned Badge)│ │(Default Role)│
                               └──────────────┘ └──────────────┘
```

### Role Model Definitions

| Role | Target Users | Capabilities & Scope |
|---|---|---|
| **`USER`** | All registered students, teachers, and visitors | Browse classes, search and download papers, participate in community discussions, request missing papers, and submit materials with voluntary public attribution. |
| **`CONTRIBUTOR`** | Users with approved public materials | Same as `USER` plus automatic inclusion on the public **Contributor Recognition Leaderboard**, special profile badges, and tracked community download impact. |
| **`ADMIN`** | Appointed community managers & moderators | Access to the **Admin Dashboard** (`/admin/dashboard`): review submissions (approve, reject, delete), manage papers (bulk upload, edit metadata, publish/draft), track subject coverage, respond to student messaging, and moderate discussions. |
| **`SUPER_ADMIN`** | Primary platform administrator (`hungrylearner786@gmail.com`) | Complete system authority. In addition to all Admin features, has exclusive access to **Admin Role Management** (`/admin/dashboard` $\rightarrow$ Admin Roles) to promote registered users, pre-authorize pending Google emails, revoke admin access, and inspect platform analytics. Cannot be demoted or revoked. |

### Two Admin Appointment Methods
1. **Method 1 — Promote Existing Registered User**: Super Admin navigates to the *Users & Contributors* tab in the Admin Dashboard, searches for an existing registered user, opens their profile modal, and promotes them to Admin.
2. **Method 2 — Pre-Authorize Email Invitation**: Super Admin enters a prospective administrator's Google email address in the *Admin Roles* tab. When that user signs in via Google for the first time, their account atomically claims the pending appointment via `claim_pending_admin_appointment()` and assumes the Admin role.
3. **Safe Revocation & Restoration**: Revoking an Admin safely and automatically restores their original role (`USER` or `CONTRIBUTOR`) stored in `users.previous_role`. No account records are deleted and contribution history remains intact.

### Authentication & Token Verification Security
- **Firebase Google Sign-In**: Authentication is handled client-side via Firebase Authentication (`signInWithPopup`).
- **Offloaded Cryptographic Token Verification**: The backend verifies Firebase ID tokens using `google.oauth2.id_token.verify_firebase_token` against Google's public OAuth2 signing certificates. Verification runs in a worker thread via `run_in_threadpool` with a 5.0-second socket timeout, guaranteeing that network delays never freeze FastAPI's main asyncio event loop.
- **Server-Side Authorization**: Administrative operations (`/api/v1/admin/*`, `/api/v1/submissions/*`, etc.) are authoritatively guarded server-side using FastAPI dependencies (`require_admin`, `require_super_admin`).
- **Zero Secret Exposure**: No database connection strings, Supabase service-role keys, or Firebase private keys are bundled in client assets.
- **Privacy Enforcement**: Contributor emails are stored in database records for administrative tracking but are stripped from all public API schemas and public page responses.

---

## 🗄️ Database & Storage

### Core Database Tables

| Table | Purpose | Primary Key |
|---|---|---|
| `classes` | School grade levels (Classes 9, 10, 11, 12) | `id INTEGER` |
| `subjects` | Academic subjects belonging to classes | `id SERIAL` |
| `papers` | Published question papers and answer keys | `id SERIAL` |
| `submissions` | Contributor material submissions awaiting review | `id UUID` |
| `submission_files` | Files attached to contributor submissions | `id UUID` |
| `users` | User profiles, canonical display names, and assigned roles (`role`, `previous_role`) | `id UUID` |
| `pending_admin_appointments` | Pre-authorized Admin email invitations created by Super Admin | `id UUID` |
| `community_posts` | Community discussions and study queries | `id UUID` |
| `community_comments` | Threaded replies on discussion posts | `id UUID` |
| `paper_likes` | User upvotes / likes on question papers | `id UUID` |
| `paper_comments` | Discussion comments on paper detail pages | `id UUID` |
| `paper_requests` | Requests for missing exam papers | `id UUID` |
| `official_notices` | Government orders, timetables, and circulars | `id SERIAL` |
| `news_updates` | Education news and exam announcements | `id UUID` |
| `audit_logs` | Immutable audit history of administrative actions | `id SERIAL` |
| `download_logs` | User download telemetry | `id UUID` |

### Supabase Storage Buckets

| Bucket Name | Access Level | Description |
|---|---|---|
| `papers` | **Public** | Published question paper and answer key PDFs served via CDN |
| `submissions` | **Private** | Uploaded contributor files awaiting administrative review |
| `official-updates` | **Public** | PDFs and attachments for official circulars and notices |
| `news-media` | **Public** | Cover images and media for educational news updates |

### Database Migrations Workflow (Supabase CLI)
The project manages database schemas through version-controlled, forward-only PostgreSQL migrations located in `supabase/migrations/`:

- **Applied Migrations (`001` through `028`)**: Fully applied and synchronized with remote Supabase production.
- **Pending Migration (`029_admin_role_management.sql`)**: Implements `previous_role`, `pending_admin_appointments`, RLS policies, and `claim_pending_admin_appointment()` stored procedure.

#### Safe Migration Commands
```bash
# 1. Link local repository to remote Supabase project
npx supabase link --project-ref fcxvrsgcvmlowehpilvr

# 2. Inspect migration history (compare local vs remote status)
npx supabase migration list

# 3. Review SQL changes before applying
cat supabase/migrations/029_admin_role_management.sql

# 4. Apply unapplied migrations (only after explicit approval)
npx supabase db push

# 5. Verify migration application
npx supabase migration list
```

---

## ⚙️ Environment Variables

### Client-Side Variables (Frontend)
Configured in `frontend/.env.local` for development and in the **Vercel Project Settings** for production. These are public build-time values.

| Variable | Required | Description | Example / Placeholder |
|---|:---:|---|---|
| `VITE_API_BASE_URL` | Optional | Backend API URL (defaults to same-origin relative `/api/v1` in production on Vercel) | `http://localhost:8000` (locally) / `""` (production) |
| `VITE_SUPABASE_URL` | ✅ | Supabase project URL | `https://YOUR_PROJECT_ID.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase public anonymous key | `YOUR_SUPABASE_ANON_KEY` |
| `VITE_FIREBASE_API_KEY` | ✅ | Firebase Web API Key | `YOUR_FIREBASE_API_KEY` |
| `VITE_FIREBASE_AUTH_DOMAIN` | ✅ | Firebase Auth Domain | `YOUR_PROJECT.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | ✅ | Firebase Project ID | `YOUR_FIREBASE_PROJECT_ID` |
| `VITE_FIREBASE_STORAGE_BUCKET` | ✅ | Firebase Storage Bucket | `YOUR_PROJECT.firebasestorage.app` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | ✅ | Firebase Sender ID | `YOUR_MESSAGING_SENDER_ID` |
| `VITE_FIREBASE_APP_ID` | ✅ | Firebase Application ID | `YOUR_FIREBASE_APP_ID` |
| `VITE_FIREBASE_MEASUREMENT_ID` | Optional | Firebase Analytics Measurement ID | `G-XXXXXXXXXX` |

### Server-Side Variables (Backend Secrets)
Configured in `backend/.env` for development and in the **Vercel Project Settings (Environment Variables)** for production. **Never commit these values to source control.**

| Variable | Required | Description | Example / Placeholder |
|---|:---:|---|---|
| `DATABASE_URL` | ✅ | Direct PostgreSQL connection string (port 5432) | `postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres` |
| `SUPABASE_URL` | ✅ | Supabase Project URL | `https://YOUR_PROJECT_ID.supabase.co` |
| `SUPABASE_ANON_KEY` | ✅ | Supabase Anon Key | `YOUR_SUPABASE_ANON_KEY` |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase Service Role Key (for storage management) | `YOUR_SUPABASE_SERVICE_ROLE_KEY` |
| `ADMIN_EMAIL` | ✅ | Authorized Admin Google account email | `admin@example.com` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed frontend origins | `http://localhost:5173,https://tn-board-portal.vercel.app` |
| `BACKEND_URL` | Optional | Backend self-reference URL | `http://localhost:8000` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Optional | Firebase Service Account JSON credentials | `{"type": "service_account", ...}` |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Optional | Filesystem path to Firebase credentials JSON | `backend/service-account.json` |

---

## 💻 Local Development Setup (WSL / Linux & Docker Compose)

The recommended and standardized local development environment uses **Docker Compose inside WSL2 (Ubuntu) or Linux**. This starts both the React frontend and FastAPI backend together in synchronized, isolated containers with health checks.

### Prerequisites
- **OS**: Windows 10/11 with WSL2 (Ubuntu 22.04+ recommended) or native Linux
- **Docker Engine & Docker Compose**: Installed inside WSL/Linux (`docker compose version` $\ge$ 2.20)
- **Node.js**: v20+ (for local CLI tooling and builds)
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/Sharruk/tn-board-portal.git
cd tn-board-portal
```

### 2. Configure Environment Variables
Copy the example environment templates:
```bash
# Root & shared environment
cp .env.example .env

# Backend configuration
cp backend/.env.example backend/.env

# Frontend configuration
cp frontend/.env.example frontend/.env.local
```
Fill in your Supabase connection URL, anonymous key, service-role key, and Firebase public credentials in the respective `.env` files.

### 3. Build & Run with Docker Compose
Run the single build and startup command from the repository root:
```bash
docker compose up --build -d
```
Both services will start in detached mode with automated health checks:
- **Frontend (React + Vite)**: [http://localhost:5000](http://localhost:5000)
- **Backend (FastAPI)**: [http://localhost:8000](http://localhost:8000)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Admin Dashboard**: [http://localhost:5000/admin/login](http://localhost:5000/admin/login)

### 4. Viewing Container Logs
Stream real-time structured logs from containers:
```bash
# Stream backend logs (FastAPI / SQLAlchemy queries / Auth logs)
docker compose logs -f backend

# Stream frontend logs (Vite dev server & reverse proxy)
docker compose logs -f frontend

# Tail last 100 log lines from backend
docker compose logs --tail=100 backend
```

### 5. Inspecting Container Health & Status
```bash
docker compose ps
```
Both containers should report status `Up (healthy)`.

### 6. Running Tests & Production Builds
```bash
# Run complete backend test suite (180 tests) inside Docker
docker exec tn-board-backend pytest

# Run specific test modules
docker exec tn-board-backend pytest tests/test_admin_roles.py -v
docker exec tn-board-backend pytest tests/test_submissions.py -v

# Validate frontend production build locally
cd frontend && npm run build
```

### 7. Stopping & Restarting Containers
```bash
# Restart only the backend service after configuration updates
docker compose restart backend

# Stop all containers (preserves container volumes and state)
docker compose down

# Stop containers and remove build cache if necessary
docker compose down --volumes
```

### 8. Troubleshooting Local Setup
- **Port Conflict (Port 5000 or 8000 already in use)**: Check for host processes using `sudo lsof -i :5000` or `sudo lsof -i :8000` and stop lingering processes.
- **Backend Health Check Failing**: Verify `backend/.env` has a reachable `SUPABASE_DATABASE_URL` (Supabase port 5432).
- **Vite Proxy Latency**: Inside Docker, the frontend proxies `/api` calls directly to `http://backend:8000` via the internal Docker bridge network (`VITE_API_PROXY_TARGET=http://backend:8000`).

---

## 🧪 Testing & Quality Assurance

### Run Backend Test Suite
The repository includes **180 comprehensive unit and integration tests** validating data access, role-based security, workflow state machines, and API schemas:
```bash
# Run tests directly inside the healthy backend container
docker exec tn-board-backend pytest
```

The test suite validates:
- **Admin Role Management (`test_admin_roles.py`)**: 20 tests validating Super Admin promotion, pre-authorization, atomic claiming, revocation, previous-role restoration, and self-demotion prevention.
- **Admin User Actions (`test_admin_users.py`)**: 4 tests validating user listings, search filters, and submission counts.
- **Material Submissions Lifecycle (`test_submissions.py`)**: 65 tests validating multi-file uploads, PDF mime validation, approved/rejected states, linked paper generation, and display-name synchronization.
- **Question Paper Catalog (`test_papers.py`)**: 35 tests covering full-text search, term expansion, class/subject filters, and proxy downloads.
- **Community & Discussions (`test_community.py`, `test_conversations.py`)**: Discussion threads, message exchanges, and moderation.
- **Authentication & Authorization (`test_auth.py`)**: Token verification offloading, role checking, and 401/403 security enforcement.

### Validate Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 🚀 Deployment Architecture (Vercel & Supabase)

Hungry Learner operates as a **unified cloud deployment on Vercel** backed by Supabase and Firebase:

```
                                  Vercel Edge Network
                         (https://tn-board-portal.vercel.app)
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
         Static Asset Routes                             API & Meta Routes
      (Vite SPA in frontend/dist)                   (Vercel Serverless Function)
                 │                                               │
         /(.*) -> index.html                     /api/(.*), /health, /docs, /openapi.json
        (Client-side routing)                                    │
                                                                 ▼
                                                           api/index.py
                                                                 │
                                                       (Adds /backend to sys.path)
                                                                 │
                                                                 ▼
                                                         app.main:app (FastAPI)
                                                                 │
                                            ┌────────────────────┴────────────────────┐
                                            ▼                                         ▼
                                   Supabase PostgreSQL                        Supabase Storage
                                   (Session Pooler: 5432)                     (Material PDFs)
```

### Vercel Serverless Architecture
- **Unified Monorepo Hosting**: The React 18 frontend and Python FastAPI backend live in the same repository and deploy together on `https://tn-board-portal.vercel.app`.
- **SPA Rewrites (`vercel.json`)**: All non-API routes (`/(.*)`) rewrite to `/index.html`, allowing React Router to manage public student pages and protected `/admin/*` routes seamlessly.
- **Serverless API Execution**: Routes under `/api/*`, `/health`, `/docs`, and `/openapi.json` route to `api/index.py`, which executes FastAPI in serverless Python 3.12 microVMs.
- **Same-Origin Production API**: In production, `resolveApiBaseUrl()` resolves to relative paths (`/api/v1/...`), eliminating CORS preflight overhead in production.

### Database Connection Strategy (Serverless vs. Docker)
In `backend/app/db/session.py`, the engine automatically detects the runtime environment:
- **On Vercel (`VERCEL=1`)**: Uses `pool_size=2, max_overflow=1` (up to 3 connections per warm instance). Since serverless microVMs handle 1 request at a time, this allows warm instance connection reuse without multiplying connection exhaustion across concurrent Lambda instances (safe against Supabase's 60-connection pool limit).
- **In Local Docker**: Uses `pool_size=10, max_overflow=5` (up to 15 connections) with TCP keepalives to handle concurrent bursts from the local development server.

### Required Production Environment Variables (Vercel Project Settings)
The following variable keys must be set in Vercel:
- `SUPABASE_DATABASE_URL`: Direct Supabase PostgreSQL connection string (Port 5432)
- `SUPABASE_URL`: Supabase project HTTPS URL
- `SUPABASE_ANON_KEY`: Supabase public anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service-role secret key (for backend storage management)
- `ADMIN_EMAIL`: Pinned Super Admin Google account email (`hungrylearner786@gmail.com`)
- `CORS_ORIGINS`: Allowed origins including `https://tn-board-portal.vercel.app`

---

## 🔄 Development & Release Workflow

1. **Feature Branching**: All enhancements and bug fixes are developed and verified on dedicated feature branches (e.g. `feature/multi-user-roles-v2`).
2. **Local Container Verification**: Test full application execution with Docker Compose and verify Pytest test suite (`180 passed`).
3. **Database Migration Synchronization**:
   - Check status: `npx supabase migration list`
   - Review pending migrations in `supabase/migrations/`
   - Apply approved migrations remotely: `npx supabase db push`
4. **Main Branch Release**:
   - Merge the approved feature branch into `main`.
   - Vercel's GitHub integration automatically builds the updated frontend and serverless backend and publishes the live production deployment.

---

## 📊 Current Status

### ✅ Implemented
- Public catalog browsing across Classes 9, 10, 11, and 12 and standard subjects.
- Full-text multi-field paper search with term expansion and filtering.
- Paper detail pages with PDF preview, YouTube explanation videos, and download tracking.
- Content-Disposition proxy downloads with clean, approved filenames.
- Community material submission flow with private storage bucket protection.
- Admin review dashboard: approve, reject, restore, and configure paper metadata.
- **Admin submission deletion**: permanent removal of pending, rejected, and approved submissions with linked paper and storage cleanup.
- **Admin paper lifecycle management**: create, edit, toggle draft/published, and permanent deletion with storage cleanup.
- Official notices, circulars, and educational news portals.
- Community discussions, question threads, upvoting, and paper requests.
- Contributor recognition leaderboard with dynamic badges and download metrics.
- Firebase Google Sign-In with server-side FastAPI token verification.

### 🟡 In Progress
- Search ranking optimizations and expanded model question paper sets.

### 🔮 Planned
- Automated push notifications for new paper releases per class.
- Interactive student practice mode and study checklists.
- Student bookmarking and personal study history.
- AI-assisted study tools and topic breakdowns.

---

## 🗺️ Roadmap

- **Phase 1: Foundation (Completed)** — Public paper library, search, download tracking, and admin CMS.
- **Phase 2: Community & Attribution (Completed)** — Material submission flow, approval pipeline, leaderboards, and community requests.
- **Phase 3: Interactive Learning (Current)** — Rich discussion threads, video embeds, and expanded resource coverage.
- **Phase 4: Personalization & Tools (Future)** — Student study planners, exam countdowns, and mobile-friendly PWA capabilities.

---

## 🔗 Hungry Learner

**TN Board Portal** is an initiative by **Hungry Learner** dedicated to empowering students through open, accessible education.

Connect with Hungry Learner across our official platforms:

- 📺 **YouTube**: [Hungry Learner on YouTube](https://www.youtube.com/@Hungry_Learner_Forever)
- 💼 **LinkedIn**: [Hungry Learner on LinkedIn](https://www.linkedin.com/company/143094994/)
- 🌐 **Web Portal**: [TN Board Portal](https://tn-board-portal.vercel.app/)

---

## 🤝 Contributing

We welcome contributions from developers, educators, and students!

1. Create a feature or bugfix branch from `dev` (`git checkout -b feature/amazing-feature`).
2. Verify tests and build locally:
   ```bash
   python -m pytest backend/tests
   cd frontend && npm run build
   ```
3. Commit your changes with descriptive messages (`git commit -m "feat: add amazing feature"`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request targeting `dev`.

---

<div align="center">

Made with ❤️ for Tamil Nadu State Board students by **Hungry Learner**

[🌐 Visit Live Site](https://tn-board-portal.vercel.app/) · [🐛 Report an Issue](https://github.com/Sharruk/tn-board-portal/issues) · [💡 Request a Feature](https://github.com/Sharruk/tn-board-portal/issues)

</div>

