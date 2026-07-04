# PROJECT_CONTEXT.md — Project Context & Vision
# TN Board Portal

> Last updated: 2026-07-03

---

## Problem Statement

Tamil Nadu State Board students (Classes 9–12) struggle to find official question papers and answer keys. Resources are scattered across:
- Government websites (often broken or outdated)
- Telegram groups (unverified, private)
- Coaching portals (paywalled)

**TN Board Portal** solves this with a single, free, publicly accessible platform.
No login. No paywall. No ads.

---

## Project Purpose

This is a **long-term software engineering portfolio project**.

Its purpose is to demonstrate competency across the full engineering stack:

| Domain | What Is Demonstrated |
|--------|----------------------|
| Frontend Engineering | React 18, Vite 5, Tailwind CSS, React Router v6 |
| Backend/BaaS | Supabase, PostgreSQL, RLS, RPC functions |
| Database Design | Normalized schema, migrations, RLS, analytics |
| System Design | Frontend-only SPA + BaaS architecture |
| Security | Row Level Security, Auth, no exposed secrets |
| Documentation | README, CHANGELOG, ROADMAP, Architecture docs |
| CI/CD | GitHub Actions, Vercel automated deployment |
| Git Workflow | Structured branching, conventional commits |
| Production Deployment | Vercel CDN, Supabase managed Postgres |

---

## Live Project

- **Production URL:** https://tn-board-portal.vercel.app
- **GitHub:** https://github.com/Sharruk/tn-board-portal
- **Current Version:** 1.0.0 (shipped 2026-07-01)
- **Deployment:** Vercel (auto-deploy from `main` branch)
- **Database:** Supabase (PostgreSQL, 14 migrations applied)

---

## Current Modules (v1.0 — LIVE)

| Module | Description | Status |
|--------|-------------|--------|
| Student Portal | Home, Class, Subject, Paper List, Paper Detail | ✅ Live |
| Search | Full-site search across papers, notices, news | ✅ Live |
| Official Notices | Circulars, timetables, govt orders with categories | ✅ Live |
| News & Updates | Education news with slugs, tags, thumbnails | ✅ Live |
| YouTube Integration | Optional YT embed links on papers and notices | ✅ Live |
| Admin Dashboard | Stats, audit logs, content status overview | ✅ Live |
| Admin Papers | Upload, edit, delete, draft/publish papers | ✅ Live |
| Admin Notices | CRUD for official notices, pin/unpin, expiry | ✅ Live |
| Admin News | CRUD for news articles with status control | ✅ Live |
| Bulk Upload | Multi-file upload with per-row progress | ✅ Live |
| Search Analytics | Every search term logged for admin insight | ✅ Live |
| Download Analytics | Atomic increment_download_count RPC | ✅ Live |
| Audit Logs | Timestamped record of every admin action | ✅ Live |
| Original Filename Preservation | `original_filename` column on uploads | ✅ Live |

---

## Next Release — v1.1 (Target: Q3 2026)

**Theme: Search Quality & SEO**

- Upgrade search to `tsvector`/`tsquery` with ranked results (migration 015)
- Year filter on all search RPCs
- `/sitemap.xml` dynamic generation
- `robots.txt`
- OpenGraph meta tags on detail pages
- Lazy loading on card components
- Admin `StatCard` reusable component
- Per-subject download trend mini-chart in admin

---

## Future Modules (Planned)

### v1.2 — Q4 2026 (Admin Maturity)
- Multi-admin support (`admin_roles` table)
- Supabase Auth MFA for admin accounts
- Dark mode toggle
- Edge Function for notice expiry sweeps
- Pagination on admin tables

### v1.3 — Q1 2027 (Accessibility & Offline)
- PWA manifest + service worker
- Web Push notifications
- WCAG 2.1 AA audit
- Rate limiting on public RPCs

### v2.0 — Q3 2027 (Platform Expansion)
- Study Materials (new content type)
- Student Accounts (optional Supabase Auth)
- Tamil Language Support (react-i18next)
- Analytics Dashboard (Recharts)
- pg_trgm fuzzy search

### v2.5 / v3.0 — 2028+ (Scale & Intelligence)
- Community Q&A
- AI search suggestions
- Mobile app (React Native)
- Automated OCR pipeline
- Multi-board support (CBSE, ICSE)
- Public read API

---

## Content Submission Vision (Future)

Students and teachers will eventually submit:
- Study Materials
- Question Papers
- Answer Keys
- Official Notices

Workflow:
```
Pending → Admin Review → Approve → Publish
```

Email submission channels:
- `papers@` — Question papers
- `materials@` — Study materials
- `support@` — General support

---

## Out of Scope (Permanently)

- Video hosting (YouTube embeds only)
- Real-time student collaboration
- Exam scheduling / timetable generation
- Fee payments or commercial features

---

## Repository Purpose for Recruiters

When a recruiter reviews this repository, they should clearly see:

1. **Architecture** — Thoughtful frontend-only + BaaS design decision
2. **Database Design** — Sequential migrations, RLS, RPCs, normalized schema
3. **Documentation** — Professional README, CHANGELOG, ROADMAP, Architecture docs
4. **Git History** — Conventional commits, clean history
5. **CI/CD** — GitHub Actions (build, lint, test, deploy) + Vercel
6. **Security** — RLS on every table, no exposed secrets, auth-gated admin
7. **Scalability** — Architecture designed to grow to v2.0 and beyond
8. **Production Quality** — Live app serving real users
