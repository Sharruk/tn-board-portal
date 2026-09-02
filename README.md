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
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

### 🌐 [Visit Live Portal → tn-board-portal.vercel.app](https://tn-board-portal.vercel.app/)

</div>

---

## 📑 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [Community Contributions & Recognition](#-community-contributions--recognition)
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
- [License](#-license)

---

## 📖 About the Project

Tamil Nadu State Board school students (Classes 9, 10, 11, and 12) preparing for examinations often encounter fragmented, incomplete, or unverified educational materials across unofficial groups and paywalled websites.

**TN Board Portal** is an open, community-driven education platform built by **Hungry Learner** to solve this problem. It provides students and educators with a fast, verified, and centralized repository of previous years' question papers, answer keys, official government circulars, syllabus updates, and video explanations — completely free and accessible without mandatory login.

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
- 📋 **Submissions Review Workflow**: Queue of pending materials submitted by students and teachers with in-browser preview, approval configuration, and rejection with feedback.
- 🗂 **Paper Lifecycle Management**: Upload new papers, edit academic metadata, toggle draft/published status, and execute **permanent deletions** with complete Supabase Storage object cleanup.
- 📦 **Bulk Upload Tool**: Upload batches of PDF files simultaneously with automated metadata parsing from standard file naming conventions.
- 📊 **Analytics & Audit Logging**: Real-time admin statistics, search query tracking, and immutable audit logs capturing admin upload, edit, and deletion history.

---

## 🤝 Community Contributions & Recognition

The platform relies on a collaborative, peer-reviewed model where students, teachers, and educators contribute past examination papers and answer keys.

```mermaid
sequenceDiagram
    autonumber
    actor Contributor as Contributor (Student / Teacher)
    participant Auth as Firebase Auth
    participant Frontend as React Frontend (Vercel)
    participant Backend as FastAPI Backend (Render)
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
- **Contributor Leaderboard**: Public leaderboard celebrating educators and students who contribute approved materials, showcasing:
  - 🏆 **Top Contributor** ($\ge 15$ approved materials or Top 3 ranking)
  - 🌟 **Active Contributor** ($\ge 5$ approved materials)
  - 🎓 **Contributor** ($\ge 1$ approved material)
  - 📈 Total downloads generated across contributed materials.

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
| **Database/Storage Client** | `@supabase/supabase-js` `2.45.4` | Client-side queries for public catalog and notices |
| **API Client** | Native `fetch` + `apiFetch` | Centralized REST client with Bearer token injection |

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

### Database, Storage & Infrastructure
| Component | Technology | Description |
|---|---|---|
| **Database** | PostgreSQL 15 (Supabase) | Relational database with 25 sequential migrations |
| **File Storage** | Supabase Storage | `papers` (public CDN), `submissions` (private), `official-updates`, `news-media` |
| **Authentication** | Firebase Authentication | Google OAuth2 identity provider |
| **Frontend Hosting** | Vercel | Global CDN hosting for React SPA |
| **Backend Hosting** | Render | Dedicated Web Service hosting for FastAPI API |
| **Automated Testing** | Pytest | Test suite with 137 unit and integration tests |

---

## 🏗️ System Architecture

The platform uses a decoupled client-server architecture:

```mermaid
graph TD
    Client["Browser / Student Client (React SPA)"] -->|Public Static Assets| Vercel["Vercel CDN (Frontend Host)"]
    Client -->|API Requests /api/v1/...| Render["Render Web Service (FastAPI Backend)"]
    Client -->|Google Sign-In| FirebaseAuth["Firebase Authentication"]

    subgraph BackendAPI ["FastAPI Backend (Render)"]
        Render --> RouteLayer["Route Layer (app/api/v1/endpoints/)"]
        RouteLayer --> ServiceLayer["Service Layer (app/services/)"]
        ServiceLayer --> RepoLayer["Repository Layer (app/repositories/)"]
        RouteLayer --> AuthDep["Auth Dependency (app/dependencies/auth.py)"]
        AuthDep -->|Verify ID Token| GoogleCert["Google OAuth2 Public Certs"]
    end

    RepoLayer -->|SQL Transactions (Port 5432)| PostgresDB[("Supabase PostgreSQL")]
    RepoLayer -->|File Storage Operations| SupabaseStorage[("Supabase Storage")]
```

### Backend Layer Responsibilities
1. **Route Layer (`app/api/v1/endpoints/`)**: Defines HTTP routes, applies dependency injection (`get_db`, `require_admin`), and maps request/response schemas.
2. **Service Layer (`app/services/`)**: Implements core business logic, input validation, term expansion, and workflow orchestration.
3. **Repository Layer (`app/repositories/`)**: Manages SQL transactions, query execution, and Supabase Storage operations.
4. **Schema Layer (`app/schemas/`)**: Declares Pydantic data contracts ensuring type safety and privacy protection.

---

## 📁 Project Structure

```
tn-board-portal/
├── backend/                         # FastAPI application (Hosted on Render)
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
│   ├── tests/                       # Automated test suite (137 tests)
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
│   ├── migrations/                  # Ordered SQL migrations (001 → 025)
│   └── README.md                    # Database documentation
├── .ai/                             # Engineering guidelines and architectural standards
├── docs/                            # Deep-dive architecture documents
├── package.json                     # Monorepo build and development scripts
└── vercel.json                      # Vercel SPA routing and build configuration
```

---

## 🔒 Authentication & Security

- **Google Sign-In**: Authentication is handled via Firebase Authentication Google Sign-In (`signInWithPopup`).
- **Cryptographic Token Verification**: The backend verifies Firebase ID tokens using `google.oauth2.id_token.verify_firebase_token` against Google's public OAuth2 signing certificates.
- **Server-Side Authorization**: Administrative operations (`/api/v1/submissions/*`, `DELETE /api/v1/papers/*`, etc.) are protected server-side with FastAPI's `require_admin` dependency, checking the authenticated account against the authorized administrator credentials.
- **Zero Secret Exposure**:
  - No secret keys, Firebase service account credentials, or database passwords are built into client bundles.
  - Supabase Service Role keys are restricted strictly to backend execution.
- **Storage Scope Protection**: File paths for storage deletion and downloads are derived from database records, preventing arbitrary client path manipulation.
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
| `users` | User profiles and assigned application roles | `id UUID` |
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

---

## ⚙️ Environment Variables

### Client-Side Variables (Frontend)
Configured in `frontend/.env.local` for development and in the **Vercel Dashboard** for production. These are public build-time values.

| Variable | Required | Description | Example / Placeholder |
|---|:---:|---|---|
| `VITE_API_BASE_URL` | ✅ | Backend API URL | `https://tn-board-portal-api.onrender.com` (or `http://localhost:8000` locally) |
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
Configured in `backend/.env` for development and in the **Render Dashboard** for production. **Never commit these values to source control.**

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

## 💻 Local Development Setup

### Prerequisites
- **Node.js**: v18.0 or later (v20+ recommended)
- **npm**: v9.0 or later
- **Python**: v3.10, v3.11, or v3.12
- **Git**
- **Supabase CLI** (`npm install -g supabase` or `brew install supabase/tap/supabase`)

### 1. Clone the Repository
```bash
git clone https://github.com/Sharruk/tn-board-portal.git
cd tn-board-portal
```

### 2. Configure Environment Variables
Copy `.env.example` to `backend/.env` and `frontend/.env.local`:
```bash
# Backend configuration
cp backend/.env.example backend/.env

# Frontend configuration
cp frontend/.env.example frontend/.env.local
```
Fill in your Supabase, Firebase, and backend API credentials.

### 3. Apply Supabase Database Migrations
Use the Supabase CLI to apply versioned migrations:
```bash
# Link your local repository to your remote Supabase project
supabase link --project-ref YOUR_PROJECT_REF

# Push all unapplied migrations (001 through 025)
supabase db push
```

### 4. Setup & Start Backend API (FastAPI)
```bash
# Navigate to backend
cd backend

# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Create and activate virtual environment (Linux/macOS)
# python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation will be available at **http://localhost:8000/docs**.

### 5. Setup & Start Frontend (React + Vite)
In a separate terminal window:
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
The application will open at **http://localhost:5173**.

---

## 🧪 Testing & Quality Assurance

### Run Backend Test Suite
The repository includes **137 unit and integration tests** across 11 test modules covering routes, services, repositories, and authentication:
```bash
# From the repository root
python -m pytest backend/tests -q
```

### Validate Frontend Production Build
Verify that all React components, styling, and assets bundle cleanly:
```bash
# From the frontend directory
cd frontend
npm run build
```

---

## 🚀 Deployment Architecture

The production environment operates across specialized cloud providers:

- **Frontend (Vercel)**:
  - Repository linked to Vercel.
  - Automatically builds `frontend/` using Vite.
  - Single Page Application rewrites configured via `vercel.json` to route all traffic to `index.html`.
  - Environment variables set in Vercel Project Settings (`VITE_API_BASE_URL` pointing to the Render backend).

- **Backend API (Render)**:
  - Deployed as a Python Web Service on Render.
  - Build command: `pip install -r backend/requirements.txt`
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (working directory: `backend`)
  - Health check endpoint: `GET /health`

- **Database & Storage (Supabase)**:
  - Supabase PostgreSQL managed database running versioned migrations.
  - Supabase Storage hosting public PDF assets and private submission queues.

---

## 🔄 Development Workflow

Follow the engineering rules documented in `.ai/`:

1. **Branching Strategy**:
   - `main`: Production-ready code.
   - `feature/*` or `fix/*`: Feature development and bugfix branches.
2. **Database Schema Evolution**:
   - Never edit existing applied migration files (`001_schema.sql` through `025_paper_description_and_fields.sql`).
   - Always create forward-only incremental migrations (`026_...sql`) and test via `supabase db push`.
3. **Pre-Commit Verification**:
   - Run the Pytest test suite (`python -m pytest backend/tests`) and verify the frontend build (`npm run build`) before pushing.

---

## 📊 Current Status

### ✅ Implemented
- Public catalog browsing across Classes 9, 10, 11, and 12 and standard subjects.
- Full-text multi-field paper search with term expansion and filtering.
- Paper detail pages with PDF preview, YouTube explanation videos, and download tracking.
- Content-Disposition proxy downloads with clean, approved filenames.
- Community material submission flow with private storage bucket protection.
- Admin review dashboard: approve, reject, restore, and configure paper metadata.
- Admin paper lifecycle management including bulk upload and **permanent deletion** with storage cleanup.
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

1. Fork the repository on GitHub.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Verify tests and build:
   ```bash
   python -m pytest backend/tests
   cd frontend && npm run build
   ```
4. Commit your changes (`git commit -m "feat: add amazing feature"`).
5. Push to the branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request on GitHub.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ for Tamil Nadu State Board students by **Hungry Learner**

[🌐 Visit Live Site](https://tn-board-portal.vercel.app/) · [🐛 Report an Issue](https://github.com/Sharruk/tn-board-portal/issues) · [💡 Request a Feature](https://github.com/Sharruk/tn-board-portal/issues)

</div>
