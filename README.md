<div align="center">

# TN State Board Portal

**Free question papers and answer keys for Tamil Nadu State Board students — Classes 9 to 12.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20Now-black?style=for-the-badge&logo=vercel)](https://tn-board-portal.vercel.app)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![Supabase](https://img.shields.io/badge/Supabase-BaaS-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Vercel](https://img.shields.io/badge/Vercel-Deployed-black?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

### 🌐 [Live Demo → tn-board-portal.vercel.app](https://tn-board-portal.vercel.app)

</div>

---

## Table of Contents

- [Why This Project Exists](#why-this-project-exists)
- [Project Status](#project-status)
- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Local Installation](#local-installation)
- [Environment Variables](#environment-variables)
- [Supabase Setup](#supabase-setup)
- [Deploying to Vercel](#deploying-to-vercel)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [License](#license)

---

## Why This Project Exists

Tamil Nadu State Board students preparing for Class 9–12 board exams often struggle to find official question papers and answer keys from previous years. Resources are scattered across government websites, unofficial Telegram groups, and private coaching portals — many of which are unreliable, incomplete, or behind paywalls.

**TN State Board Portal** solves this by providing a single, free, and openly accessible platform where students can instantly find, preview, and download question papers and answer keys — organized by class, subject, and exam type.

No login. No paywall. No ads.

---

## Project Status

**Deployment:** ✅ Production — Live at [tn-board-portal.vercel.app](https://tn-board-portal.vercel.app)

### Completed Features

| Feature | Status |
|---------|:------:|
| Browse by Class & Subject | ✅ |
| Full-text Search | ✅ |
| PDF Download via CDN | ✅ |
| Admin Authentication | ✅ |
| Paper Upload (single & bulk) | ✅ |
| Edit Paper Metadata | ✅ |
| Delete Papers | ✅ |
| Visibility Control (draft/published) | ✅ |
| Download Analytics | ✅ |
| Admin Audit Log | ✅ |
| Content Status Overview | ✅ |

---

## Features

### 🎓 Student Features

- 📚 **Browse by Class & Subject** — Navigate a clear hierarchy: Class → Subject → Papers
- 🔍 **Full-text Search** — Search by subject name, exam type, class, year, or title
- 📄 **Paper Detail View** — View metadata and download count before downloading
- ⬇️ **One-click PDF Download** — Files served directly from Supabase Storage CDN
- 🚫 **No account required** — Fully open access for all students

### 🛡️ Admin Features

- 🔐 **Secure Login** — Supabase Auth (email/password); no public registration
- 📋 **Dashboard** — At-a-glance stats: total papers, subjects, classes, download counts
- 🗂 **Paper Management** — Upload, edit metadata, toggle draft/published, delete
- 📦 **Bulk Upload** — Upload multiple papers simultaneously with metadata
- 📊 **Content Status** — Cross-subject view of published vs. draft coverage
- 📝 **Audit Log** — Timestamped record of every admin action

---

## Screenshots

Screenshots coming soon. The application is live at https://tn-board-portal.vercel.app

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│                                                         │
│   React 18 + Vite 5 + Tailwind CSS 3                   │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │  Public  │ │  Search  │ │  Paper   │ │  Admin   │  │
│   │  Pages   │ │   Page   │ │  Detail  │ │ Dashboard│  │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│        └────────────┴────────────┴─────────────┘        │
│                           │                             │
│        services/ data-access layer                      │
│        papers.js · search.js · classes.js · admin.js   │
└───────────────────────────┼─────────────────────────────┘
                            │  Supabase JS SDK
                            ▼
┌─────────────────────────────────────────────────────────┐
│                       Supabase                          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ PostgreSQL  │  │     Auth     │  │    Storage    │  │
│  │             │  │              │  │               │  │
│  │ papers      │  │ Admin users  │  │ PDF files     │  │
│  │ subjects    │  │ (email/pw)   │  │ (public CDN)  │  │
│  │ classes     │  └──────────────┘  └───────────────┘  │
│  │ audit_logs  │                                        │
│  │ search_queries         RLS + SECURITY DEFINER        │
│  └─────────────┘               RPC functions            │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│               Vercel (Static Hosting)                   │
│         Vite build → dist/ → global CDN edge            │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Frontend-only architecture** | No custom server or API layer |
| **React + Supabase** | All UI in React; all data in Supabase |
| **No custom backend** | Supabase handles DB, Auth, and Storage |
| **RLS-secured database access** | PostgreSQL Row Level Security on every table |
| **Static deployment** | Vite SPA deployed to Vercel global CDN |

> **Architecture decision:** This project intentionally uses a frontend-only React + Supabase architecture. Do not introduce a separate backend unless there is a strong technical requirement. All authorization is enforced by PostgreSQL Row Level Security policies and `SECURITY DEFINER` RPC functions — not application code.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI Framework | React 18 |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS 3 |
| Routing | React Router DOM 6 |
| Backend-as-a-Service | Supabase |
| Database | PostgreSQL (via Supabase) |
| Authentication | Supabase Auth |
| File Storage | Supabase Storage |
| Hosting | Vercel |

---

## Local Installation

### Prerequisites

- **Node.js** 20 or later ([download](https://nodejs.org))
- **npm** 10 or later (bundled with Node.js)
- A **Supabase project** — free tier is sufficient ([create one](https://supabase.com/dashboard))

### 1. Clone the repository

```bash
git clone https://github.com/Sharruk/tn-board-portal.git
cd tn-board-portal
```

### 2. Install dependencies

```bash
cd frontend
npm install
```

### 3. Configure environment variables

Copy the example file and fill in your Supabase credentials:

```bash
# From the repo root:
cp .env.example frontend/.env.local
```

Edit `frontend/.env.local`:

```env
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

> Get these values from: **Supabase Dashboard → Project Settings → API**

### 4. Apply database migrations

See [Supabase Setup](#supabase-setup) below.

### 5. Start the development server

```bash
cd frontend
npm run dev
```

The app runs at **http://localhost:5173** by default.

### 6. Production build

```bash
cd frontend
npm run build    # outputs to frontend/dist/
npm run preview  # preview the production build locally
```

---

## Environment Variables

Both variables are **build-time only** — Vite embeds them at `npm run build`. The anon key is intentionally public; Supabase Row Level Security enforces all access control independently of this key.

| Variable | Required | Description |
|----------|:--------:|-------------|
| `VITE_SUPABASE_URL` | ✅ | Your Supabase project URL, e.g. `https://xxxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anonymous/public key — safe to expose |

**Where to set them:**

| Context | Location |
|---------|----------|
| Local development | `frontend/.env.local` (gitignored — never commit this file) |
| Vercel deployment | Vercel Dashboard → Project → Settings → Environment Variables |

---

## Supabase Setup

### 1. Database migrations

Apply the SQL migrations **in order** using the Supabase SQL Editor (**Dashboard → SQL Editor → New query**). Run each file completely before moving to the next.

| # | File | What it does |
|---|------|-------------|
| 1 | `supabase/migrations/001_schema.sql` | Creates tables: `classes`, `subjects`, `papers`, `audit_logs`, `search_queries` |
| 2 | `supabase/migrations/002_seed_data.sql` | Seeds Classes 9–12 and all standard subjects |
| 3 | `supabase/migrations/003_rls_policies.sql` | Row Level Security: public read, admin-only write |
| 4 | `supabase/migrations/004_functions.sql` | RPC: `increment_download_count`, `get_admin_stats`, `get_content_status` |
| 5 | `supabase/migrations/005_search_analytics.sql` | Search query logging and analytics support |
| 6 | `supabase/migrations/006_search_rpc.sql` | RPC: `search_papers` (full-text search) |
| 7 | `supabase/migrations/007_paper_status.sql` | Draft/published status workflow for papers |

### 2. Storage bucket

In **Supabase Dashboard → Storage**:

1. Click **New bucket**
2. Name it `papers`
3. Set it to **Public** (so PDFs are accessible via CDN URL without auth)

### 3. Admin users

Admin access is managed entirely through Supabase Auth — there is no public registration flow.

1. Go to **Dashboard → Authentication → Users**
2. Click **Add user** → enter the admin's email and password
3. The app identifies admin sessions by authenticated Supabase Auth status

---

## Deploying to Vercel

### Initial setup

1. Push the repository to GitHub
2. Go to [vercel.com](https://vercel.com) → **Add New Project**
3. Import `tn-board-portal` from GitHub
4. Configure the project settings:

| Setting | Value |
|---------|-------|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite _(auto-detected)_ |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

5. Add environment variables under **Settings → Environment Variables**:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
6. Click **Deploy**

### SPA routing

The `vercel.json` at the repository root configures a catch-all rewrite so React Router routes (`/search`, `/admin`, `/class/10`, etc.) work correctly on direct navigation and page refresh:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### Subsequent deploys

Vercel automatically redeploys on every push to the `main` branch.

---

## Project Structure

```
tn-board-portal/
├── frontend/                        # React application (Vercel root)
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx                 # Application entry point
│       ├── index.css                # Global styles
│       ├── components/              # Reusable UI components
│       │   ├── Navbar.jsx
│       │   ├── Footer.jsx
│       │   ├── SearchBar.jsx
│       │   ├── PaperCard.jsx
│       │   ├── ClassCard.jsx
│       │   ├── Breadcrumb.jsx
│       │   ├── LoadingSpinner.jsx
│       │   ├── ErrorMessage.jsx
│       │   └── admin/
│       │       ├── AdminLayout.jsx  # Admin section shell/layout
│       │       └── ProtectedRoute.jsx  # Auth guard for admin routes
│       ├── contexts/
│       │   └── AuthContext.jsx      # Supabase Auth session state
│       ├── hooks/
│       │   └── useFetch.js          # Generic data-fetching hook
│       ├── layouts/
│       │   └── MainLayout.jsx       # Public page layout wrapper
│       ├── lib/
│       │   └── supabase.js          # Supabase client (reads env vars)
│       ├── pages/                   # Route-level page components
│       │   ├── HomePage.jsx
│       │   ├── ClassPage.jsx
│       │   ├── SubjectPage.jsx
│       │   ├── PaperListPage.jsx
│       │   ├── PaperDetailPage.jsx
│       │   ├── SearchPage.jsx
│       │   ├── NotFoundPage.jsx
│       │   └── admin/
│       │       ├── LoginPage.jsx
│       │       ├── DashboardPage.jsx
│       │       ├── PapersPage.jsx       # Paper list, edit, delete
│       │       ├── BulkUploadTab.jsx    # Multi-file upload UI
│       │       └── ContentStatusPage.jsx
│       ├── router/
│       │   └── index.jsx            # React Router route definitions
│       ├── services/                # Supabase data-access layer
│       │   ├── papers.js            # CRUD for papers
│       │   ├── search.js            # Full-text search via search_papers RPC
│       │   ├── classes.js           # Fetch classes
│       │   ├── subjects.js          # Fetch subjects
│       │   └── admin.js             # Admin stats, audit log, content status
│       └── utils/
│           └── download.js          # PDF download helper
│
├── supabase/
│   ├── migrations/                  # SQL migrations — apply in order
│   │   ├── 001_schema.sql
│   │   ├── 002_seed_data.sql
│   │   ├── 003_rls_policies.sql
│   │   ├── 004_functions.sql
│   │   ├── 005_search_analytics.sql
│   │   ├── 006_search_rpc.sql
│   │   └── 007_paper_status.sql
│   └── README.md
│
├── vercel.json                      # SPA catch-all rewrite for React Router
├── .env.example                     # Environment variable template
├── .gitignore
└── README.md
```

---

## Roadmap

### 🔜 Short-term

- [ ] **Screenshots** — Capture and publish app screenshots
- [ ] **Supabase CLI migrations** — Replace manual SQL Editor with `supabase db push`
- [ ] **Paper ratings** — Students can rate answer key quality

### 🗓 Medium-term

- [ ] **Student accounts** — Save favourites and personal download history
- [ ] **Analytics dashboard** — Per-subject and per-class download trend charts for admins
- [ ] **Push notifications** — Alert students when new papers are uploaded for their class

### 🔭 Long-term

- [ ] **Multi-board support** — Extend to CBSE and ICSE question banks
- [ ] **OCR text extraction** — Make scanned PDFs searchable by content
- [ ] **Mobile app** — React Native wrapper for offline PDF viewing

---

## Contributing

Contributions are welcome! This is a documentation-first, architecture-stable project.

### Ground rules

1. **Do not introduce a server-side backend.** The frontend-only React + Supabase architecture is intentional. All auth and data access must go through Supabase RLS and RPC functions.
2. **Do not modify migrations that have already been applied to production.** Add new migration files instead.
3. **Verify the build locally** before opening a pull request:

```bash
cd frontend && npm install && npm run build
```

### How to contribute

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/tn-board-portal.git
cd tn-board-portal

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make your changes, then verify the build
cd frontend && npm install && npm run build

# 5. Commit and push
git commit -m "feat: describe your change"
git push origin feature/your-feature-name

# 6. Open a Pull Request on GitHub
```

For bug reports or feature requests, open a [GitHub Issue](https://github.com/Sharruk/tn-board-portal/issues).

---

## Acknowledgements

| Tool | Role |
|------|------|
| [React](https://react.dev) | UI framework |
| [Vite](https://vitejs.dev) | Build tool and dev server |
| [Tailwind CSS](https://tailwindcss.com) | Utility-first styling |
| [React Router](https://reactrouter.com) | Client-side routing |
| [Supabase](https://supabase.com) | Database, Auth, and Storage |
| [Vercel](https://vercel.com) | Hosting and global CDN |

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2025 Sharruk

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

Made with ❤️ for Tamil Nadu State Board students

[🌐 Visit Live Site](https://tn-board-portal.vercel.app) · [🐛 Report a Bug](https://github.com/Sharruk/tn-board-portal/issues) · [💡 Request a Feature](https://github.com/Sharruk/tn-board-portal/issues)

</div>
