# Changelog

All notable changes to TN Board Portal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Placeholder for next release work

---

## [1.0.0] — 2026-07-01

### Added
- **Student Portal** — Public-facing portal with Home, Class, Subject, Paper List, Paper Detail, and Search pages
- **Admin Dashboard** — Protected `/admin` section with sidebar layout and `ProtectedRoute` component
- **Authentication** — Supabase Auth (email/password) with persistent session via `AuthContext`
- **Papers module** — Upload, edit, delete, and publish question papers and answer keys
- **Paper status system** — `draft` | `published` | `archived` status column (migration 007)
- **Bulk Upload** — Multi-file upload with per-row progress tracking (`BulkUploadTab`)
- **Official Notices** — `official_notices` table with category, pin/unpin, expiry date, view/download counters
- **Notice search** — `search_notices()` PostgreSQL RPC with ILIKE filtering
- **News & Updates** — `news_updates` table with slugs, tags, status, thumbnail, and `search_news()` RPC
- **YouTube Links** — Optional YouTube embed URL on papers and official notices
- **PDF Downloads** — Atomic `increment_download_count()` RPC, direct Supabase Storage CDN links
- **Original Filename Preservation** — `original_filename` column (migration 013); displayed on paper detail and notice detail pages
- **Full-site Search** — `search_papers()`, `search_notices()`, `search_news()` RPCs unified on the `/search` page
- **Search Analytics** — `search_queries` table records every query term and result count for admin insight
- **Audit Logs** — `audit_logs` table records every admin action (upload, bulk upload, edit, delete, login) with IP address
- **Content Status Page** — Admin view listing all papers with current status at a glance (`/admin/content-status`)
- **Row Level Security** — Comprehensive RLS policies on all tables for `anon` and `authenticated` roles
- **Database Migrations** — 14 sequential, idempotent migrations covering schema, seed data, RLS, RPCs, analytics, notices, news, and filename preservation
- **Supabase Storage** — Three buckets: `papers`, `official-updates`, `news-media`, each with public-read / authenticated-write policies
- **Vercel Deployment** — SPA rewrite rule in `vercel.json`; production served from `main` branch
- **React Router v6** — Client-side routing for all public and admin routes
- **Tailwind CSS v3** — Utility-first styling with PostCSS and Autoprefixer

### Known Issues
- Search uses ILIKE only; no full-text ranking or typo tolerance
- No rate limiting on public RPC calls (`search_papers`, `search_notices`, `search_news`)
- Admin area supports a single shared Supabase Auth account; no multi-admin role management
- No email notification system for new published content

---

## [1.1.0] — Planned Q3 2026

### Added
- Full-text search upgrade: `tsvector` / `tsquery` with relevance ranking (replaces ILIKE in `search_papers`)
- Year filter added to `search_papers()` RPC (migration 015)
- Sitemap generation (`/sitemap.xml`) served via Vercel serverless function
- `robots.txt` served from project root
- Image lazy-loading on all card components

### Changed
- Search query debounce raised from 300 ms to 400 ms to reduce unnecessary RPC calls
- Admin dashboard stat cards refactored into reusable `StatCard` component

### Fixed
- `search_papers()` LIMIT applied before ORDER BY — corrected ordering semantics in migration 015
- Notice category badge colour contrast fails WCAG AA — updated Tailwind classes

---

## [1.2.0] — Planned Q4 2026

### Added
- Multi-admin support: `admin_roles` table with `super_admin` and `editor` roles
- Supabase Edge Function for scheduled expiry sweep of `official_notices`
- Dark mode toggle persisted to `localStorage`, respects `prefers-color-scheme`

### Changed
- Admin login page redesigned with OTP support via Supabase Auth MFA

### Fixed
- Occasional Supabase 406 error when `Accept` header is missing in service calls
- Bulk upload silently skips duplicate rows — now surfaces a visible warning per row

---

## [1.3.0] — Planned Q1 2027

### Added
- PWA manifest and service worker for offline paper viewing
- Push notifications for new pinned notices (Web Push API + Supabase Edge Function)
- Accessibility audit pass targeting WCAG 2.1 AA
- `original_filename` displayed in admin papers list and bulk upload results

### Fixed
- Keyboard focus trap in admin modal dialogs
- Mobile navbar z-index overlap with PDF embed viewer

---

## [2.0.0] — Planned Q3 2027

### Added
- **Study Materials** — New content type separate from question papers, with its own table and RPC
- **Student Accounts** — Optional Supabase Auth registration for bookmarks and download history
- **Tamil Language Support** — i18n with `react-i18next` (Tamil + English toggle)
- **Analytics Dashboard** — Page views, search trends, download trends charted with Recharts
- `pg_trgm` trigram indexes for fuzzy search matching

### Changed
- Full Supabase Auth MFA rollout mandatory for all admin accounts
- Home page rebuilt with animated hero section and dynamic pinned-content carousel

### Removed
- Legacy `is_visible` boolean column removed from `papers` table (status column is the sole truth)

---

[Unreleased]: https://github.com/Sharruk/tn-board-portal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Sharruk/tn-board-portal/releases/tag/v1.0.0
[1.1.0]: https://github.com/Sharruk/tn-board-portal/releases/tag/v1.1.0
[1.2.0]: https://github.com/Sharruk/tn-board-portal/releases/tag/v1.2.0
[1.3.0]: https://github.com/Sharruk/tn-board-portal/releases/tag/v1.3.0
[2.0.0]: https://github.com/Sharruk/tn-board-portal/releases/tag/v2.0.0
