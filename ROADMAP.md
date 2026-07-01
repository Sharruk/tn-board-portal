# ROADMAP — TN Board Portal

> Last updated: 2026-07-01
> This roadmap reflects real planned work. Dates are targets, not guarantees.

---

## Current — v1.0 (Shipped)

The portal is live on Vercel with the following capabilities:

| Area | Status |
|------|--------|
| Student Portal (Home, Class, Subject, Paper, Search, News, Notices) | ✅ Live |
| Admin Dashboard (Papers, Notices, News, Content Status, Bulk Upload) | ✅ Live |
| Supabase Auth (single admin account, email/password) | ✅ Live |
| Paper status system (draft / published / archived) | ✅ Live |
| Three storage buckets (papers, official-updates, news-media) | ✅ Live |
| 14 database migrations with full RLS and RPCs | ✅ Live |
| Search across papers, notices, and news via ILIKE RPCs | ✅ Live |
| Search analytics, audit logs, download counters, view counters | ✅ Live |
| Original filename preservation on uploads | ✅ Live |
| Vercel SPA deployment with rewrite rules | ✅ Live |

---

## Next Release — v1.1 (Q3 2026)

**Theme: Search Quality & SEO**

- [ ] Upgrade `search_papers()` to use `tsvector` / `tsquery` for ranked full-text results
- [ ] Add year-based filter to all search RPCs (migration 015)
- [ ] Fix LIMIT/ORDER BY sequencing bug in `search_papers()` (migration 015)
- [ ] Generate `/sitemap.xml` dynamically (Vercel serverless function or Edge Function)
- [ ] Add `robots.txt` to project root
- [ ] Implement meta tags (`og:title`, `og:description`, `og:image`) on Notice and News detail pages
- [ ] Image lazy-loading on `NewsCard`, `NoticeCard`, and `PaperCard`
- [ ] Refactor admin dashboard stats into reusable `StatCard` component
- [ ] Add per-subject download trend mini-chart to admin dashboard

---

## Future Plans — v1.2 (Q4 2026)

**Theme: Admin Maturity & Reliability**

- [ ] Multi-admin support: `admin_roles` table with `super_admin` and `editor` roles
- [ ] Supabase Auth MFA (OTP) opt-in for admin accounts
- [ ] Dark mode toggle (localStorage + `prefers-color-scheme`)
- [ ] Supabase Edge Function for scheduled notice expiry sweeps
- [ ] Fix silent Bulk Upload duplicate handling — surface visible per-row warning
- [ ] Admin notices list sortable by category, year, and created date
- [ ] Pagination on admin Papers, Notices, and News tables (currently loads all rows)

---

## Future Plans — v1.3 (Q1 2027)

**Theme: Accessibility & Offline**

- [ ] PWA manifest + service worker for offline paper caching
- [ ] Web Push notifications for newly pinned notices (via Supabase Edge Function)
- [ ] WCAG 2.1 AA accessibility audit and remediation
- [ ] Keyboard focus trap fix in admin modal dialogs
- [ ] Rate limiting on public RPC calls via Supabase Edge Function middleware
- [ ] `original_filename` shown in admin paper list table column
- [ ] Mobile navbar z-index and PDF embed viewer overlap fix

---

## Future Plans — v2.0 (Q3 2027)

**Theme: Platform Expansion**

- [ ] **Study Materials** — New content type (notes, guides) with separate table and storage bucket
- [ ] **Student Accounts** — Optional registration via Supabase Auth for bookmarks and download history
- [ ] **Tamil Language Support** — Full i18n with `react-i18next` (Tamil and English)
- [ ] **Analytics Dashboard** — Page views, search trends, and download trends charted with Recharts
- [ ] `pg_trgm` trigram indexes for fuzzy, typo-tolerant search
- [ ] Home page animated hero section and pinned-content carousel
- [ ] Remove legacy `is_visible` column from `papers` (status is sole source of truth)

---

## Long-Term Vision — v2.5 / v3.0 (2028+)

**Theme: Scale & Intelligence**

- Community Q&A section tied to specific papers
- AI-assisted search suggestions and related-paper recommendations
- District-level analytics for education administrators
- Mobile app (React Native) using the same Supabase backend
- Automated paper OCR pipeline to make paper content searchable as text
- Multi-board support (CBSE, ICSE alongside TN State Board)
- API-first architecture with public read API for third-party integrations

---

## Not Planned

The following are explicitly **out of scope** for the foreseeable future:

- Video hosting (YouTube embed links will remain the approach)
- Real-time collaboration / commenting by students
- Exam scheduling / timetable generation
- Fee payment or any commercial transaction features

---

> This roadmap is maintained by the project owner. To propose a roadmap item, open a [GitHub Discussion](https://github.com/Sharruk/tn-board-portal/discussions).
