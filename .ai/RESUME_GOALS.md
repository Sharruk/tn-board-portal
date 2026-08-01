# RESUME_GOALS.md — Resume & Portfolio Goals
# TN Board Portal

> Every improvement to this project should increase its value as a portfolio piece.
> This document tracks what skills this project demonstrates and what to prioritize next.

---

## Target Roles

This project is designed to impress hiring managers for:

- **Software Engineer** (full-stack)
- **Frontend Engineer**
- **Backend Engineer**
- **Full Stack Engineer**
- **DevOps / Platform Engineer**
- **Open Source Contributor**

Target companies: Google, Microsoft, Amazon, Atlassian, GitHub, Vercel, Supabase, Notion, Linear, Figma, and similar.

---

## What This Project Currently Demonstrates

### Engineering

| Skill | Evidence |
|-------|---------|
| React 18 | Functional components, hooks, context, router |
| Vite 5 | Build tool, HMR, production optimization |
| Tailwind CSS 3 | Utility-first responsive styling |
| React Router v6 | Nested layouts, protected routes, dynamic params |
| Supabase JS SDK | Auth, Storage, PostgREST, RPC calls |

### Database & Backend

| Skill | Evidence |
|-------|---------|
| PostgreSQL | Normalized schema, relationships, constraints |
| Database migrations | 14 sequential, versioned, idempotent migrations |
| Row Level Security | Per-table, per-role policies for every table |
| PostgreSQL RPC functions | Custom SECURITY DEFINER functions for search, stats, counters |
| Storage design | 3 buckets with appropriate access policies |

### Architecture

| Skill | Evidence |
|-------|---------|
| System Design | Frontend SPA + BaaS (intentional, well-documented decision) |
| Service layer pattern | All DB access through `services/` — no direct calls from UI |
| Separation of concerns | lib → services → components → pages layering |
| Atomic operations | Counter increments via PostgreSQL RPC (race-condition safe) |

### Security

| Skill | Evidence |
|-------|---------|
| RLS-based auth | Authorization at DB level, not application level |
| Auth flow | Supabase Auth + ProtectedRoute + AuthContext |
| Secret management | Build-time env vars, no secrets in code |
| Audit logging | Every admin action recorded |

### Documentation

| Skill | Evidence |
|-------|---------|
| README quality | Comprehensive setup, architecture, deployment guide |
| CHANGELOG | Follows Keep a Changelog, SemVer versioning |
| ROADMAP | Realistic future plans with themes and timelines |
| Architecture docs | `docs/ARCHITECTURE.md` with diagrams and rationale |
| Contributing guide | Clear ground rules, build verification requirement |

### DevOps & Deployment

| Skill | Evidence |
|-------|---------|
| Vercel deployment | SPA rewrite, env var config, auto-deploy from main |
| GitHub Actions | Build, lint, dependency audit workflows |
| CI pipeline | `npm run build` passes on every push |

### Git Discipline

| Skill | Evidence |
|-------|---------|
| Conventional commits | Consistent `feat:`, `fix:`, `docs:` prefix format |
| Meaningful history | Each commit is one logical change |
| Branching | Feature branches, merge to main |

---

## What to Build Next (Highest Portfolio Value)

Prioritized by recruiter impact:

### Tier 1 — Immediate Impact
1. **Full-text search upgrade** (`tsvector`/`tsquery` with GIN index) — shows PostgreSQL depth
2. **Lazy loading + code splitting** — shows frontend performance awareness
3. **Sitemap.xml generation** — shows SEO and Vercel serverless knowledge
4. **OpenGraph meta tags** — shows real-world web standards knowledge
5. **StatCard reusable component** — shows component architecture maturity

### Tier 2 — Strong Impact
6. **Dark mode** — shows CSS architecture (CSS variables) and localStorage
7. **Admin pagination** — shows "scale awareness" mindset
8. **Multi-admin support** — shows RBAC database design
9. **Supabase Edge Function** — shows serverless/Edge computing skill
10. **PWA manifest** — shows progressive web app knowledge

### Tier 3 — Big Differentiators
11. **Student accounts** — full auth flow for two user types
12. **Analytics dashboard** — Recharts, data visualization
13. **Tamil language support** — i18n/l10n knowledge
14. **React Native mobile app** — mobile development
15. **OCR pipeline** — AI/ML integration

---

## Talking Points for Interviews

When asked about this project:

**"Tell me about a technical challenge you solved."**
> "I needed to implement full-site search across three different tables (papers, notices, news) with different schemas. I used PostgreSQL's ILIKE queries in SECURITY DEFINER RPC functions, called in parallel with Promise.all() in the frontend, with a 400ms debounce. Now I'm upgrading it to tsvector/tsquery for ranked results."

**"How do you handle security?"**
> "Security is enforced at the database level using PostgreSQL Row Level Security on every table. The Supabase anon key is intentionally public — it's equivalent to a public API key. What it can access is determined entirely by RLS policies, not by the key itself."

**"How does your CI/CD work?"**
> "GitHub Actions verifies the build on every push. Pushing to main automatically triggers a Vercel production deployment. The anon key is stored in Vercel environment variables, never committed to Git."

**"Why Supabase instead of a custom backend?"**
> "Deliberate architectural decision. Supabase gives me managed Postgres with Auth, Storage, and CDN out of the box. This lets me focus on product quality — schema design, RLS policies, meaningful RPC functions — instead of maintaining infrastructure. I can always introduce a serverless layer (Vercel Functions or Supabase Edge Functions) when there's a specific need."

---

## GitHub Repository Goals

When a recruiter visits https://github.com/Sharruk/tn-board-portal:

- README should make them want to clone it in 30 seconds
- Commit history should show consistency and discipline
- CHANGELOG should show version maturity
- Actions tab should show green CI badges
- Code quality should hold up under review
