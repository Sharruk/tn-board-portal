# CHANGE_HISTORY.md — Implementation Change History
# TN Board Portal

> Log every significant implementation session here.
> This file is the AI's memory of what has already been done.
> Always read this before implementing anything new.

---

## Format

```
### [DATE] — Brief Title
Implemented by: [AI assistant name or "Developer"]
Session type: Feature | Bug Fix | Refactor | Documentation | Database | DevOps

What was done:
- [Summary of changes]

Files created:
- [List of new files]

Files modified:
- [List of changed files]

Migrations applied:
- [Migration number and name]

Build status: ✅ Pass | ❌ Fail (reason)

Notes:
- [Any caveats, known issues, or follow-up needed]
```

---

## History

---

### [Pre-2026-07-01] — Initial v1.0 Development

**Implemented by:** Developer
**Session type:** Feature (full initial build)

**What was done:**
- Built the complete v1.0 student portal and admin dashboard
- Implemented all 14 database migrations
- Set up three Supabase Storage buckets
- Configured Vercel deployment with SPA rewrite
- Set up GitHub Actions (build, lint, dependency-audit)
- Created public documentation (README, CHANGELOG, ROADMAP, CONTRIBUTING, docs/ARCHITECTURE.md)

**Modules shipped:**
- Student Portal: Home, Class, Subject, PaperList, PaperDetail, Search, OfficialNotices, NoticeDetail, News, NewsDetail
- Admin Dashboard: Papers, Notices, News, BulkUpload, ContentStatus, AuditLog
- Auth: Supabase Auth + AuthContext + ProtectedRoute
- Services: papers.js, classes.js, subjects.js, notices.js, news.js, search.js, admin.js
- Utils: download.js

**Migrations applied:**
- 001_schema.sql — Base schema (classes, subjects, papers, audit_logs, search_queries)
- 002_seed_data.sql — Classes 9–12 and subjects seed
- 003_rls_policies.sql — RLS on papers, classes, subjects
- 004_functions.sql — get_admin_stats, increment_download_count, get_content_status
- 005_search_analytics.sql — search_queries table
- 006_search_rpc.sql — search_papers() ILIKE RPC
- 007_paper_status.sql — status column (draft|published|archived)
- 008_official_notices.sql — official_notices table, search_notices RPC
- 009_fix_notices_grants.sql — GRANT fixes for notices RPCs
- 010_add_youtube_url_to_official_notices.sql — youtube_url column on notices
- 011_news_updates.sql — news_updates table, search_news RPC
- 012_fix_news_grants.sql — GRANT fixes for news RPCs
- 013_preserve_original_filenames.sql — original_filename column
- 014_update_search_papers_rpc.sql — Updated search_papers RPC

**Build status:** ✅ Pass

**Notes:**
- Known issue: search uses ILIKE (no relevance ranking) — planned fix in v1.1 migration 015
- Known issue: no rate limiting on public RPCs — planned in v1.3
- Known issue: single admin account (no multi-admin) — planned in v1.2

---

### [2026-07-03] — .ai/ Documentation Folder Created

**Implemented by:** Antigravity (AI Assistant)
**Session type:** Documentation

**What was done:**
- Created the `.ai/` private AI operating manual folder
- Created 16 documentation files covering all aspects of the project
- Added `.ai/` to `.gitignore`

**Files created:**
- `.ai/AGENTS.md` — Master AI operating manual
- `.ai/PROJECT_CONTEXT.md` — Project context, current modules, roadmap
- `.ai/DEVELOPMENT_RULES.md` — Development rules and workflow
- `.ai/ARCHITECTURE_RULES.md` — Architecture rules, layer responsibilities, data flows
- `.ai/DATABASE_RULES.md` — Migration guide, schema reference, RPC/RLS docs
- `.ai/CODING_STANDARDS.md` — Component structure, service patterns, conventions
- `.ai/FEATURE_WORKFLOW.md` — Feature implementation 8-step workflow
- `.ai/BUG_FIX_WORKFLOW.md` — Bug fix workflow and common bug patterns
- `.ai/GIT_WORKFLOW.md` — Git branching, commit format, what to commit
- `.ai/DOCUMENTATION_RULES.md` — Documentation standards, when to update what
- `.ai/GITHUB_RULES.md` — GitHub labels, milestones, issues, releases, CI/CD
- `.ai/SECURITY_GUIDELINES.md` — RLS, auth, storage, env var security
- `.ai/PERFORMANCE_GUIDELINES.md` — Bundle size, DB queries, indexes, search debounce
- `.ai/RESUME_GOALS.md` — Portfolio value, interview talking points
- `.ai/PROMPTS.md` — Saved AI prompts for future sessions
- `.ai/DECISIONS.md` — 8 architectural decision records (ADR-001 through ADR-008)
- `.ai/CHANGE_HISTORY.md` — This file

**Files modified:**
- `.gitignore` — Added `.ai/` entry

**Build status:** ✅ Pass (no application code changed)

**Notes:**
- Application code was NOT modified in this session
- All documentation is based on actual project analysis
- DECISIONS.md documents 8 existing architectural choices made pre-v1.0
- Next session should implement actual v1.1 features (search upgrade, lazy loading, sitemap)

---

### [2026-07-04] — .ai/ Folder Made Version-Controlled

**Implemented by:** Antigravity (AI Assistant)
**Session type:** Documentation / DevOps

**What was done:**
- Changed AI documentation strategy: `.ai/` folder is now intentionally version-controlled
- Removed `.ai/` entry (and its comment block) from `.gitignore`
- Added `## Repository Visibility` section to `AGENTS.md`
- Added security constraint to `AGENTS.md` Critical Constraints table: never store secrets in `.ai/`
- Updated `AGENTS.md` "Private vs. Public Files" section → replaced with "Repository Visibility" + "What Is Committed vs. Not Committed"
- Updated `GIT_WORKFLOW.md`: removed "Never commit .ai/" rule; replaced with "Never store secrets in .ai/"
- Updated `GIT_WORKFLOW.md`: removed `.ai/**` from Never Commit list
- Updated `DOCUMENTATION_RULES.md`: updated `.ai/` description from "never committed" to "intentionally version-controlled"

**Rationale:**
- Repository is currently private; sharing AI memory across environments (Antigravity, Cursor, Replit, Codex, Claude Code, GitHub Copilot) outweighs the risk of committing it while private
- Security audit confirmed no secrets, API keys, or credentials exist in any `.ai/` file

**Files created:**
- None

**Files modified:**
- `.gitignore` — Removed `.ai/` ignore entry
- `.ai/AGENTS.md` — Added Repository Visibility section, updated constraints, updated commit guide
- `.ai/GIT_WORKFLOW.md` — Updated NEVER rules and commit checklist
- `.ai/DOCUMENTATION_RULES.md` — Updated .ai/ description
- `.ai/CHANGE_HISTORY.md` — This entry

**Migrations applied:**
- None

**Build status:** ✅ Pass (no application code changed)

**Notes:**
- Before making the repository public, review whether `.ai/` should remain or move to a separate private repository
- All 17 `.ai/` files were security-scanned — no credentials found
- No duplicate rules found across files; cross-references verified consistent

---

### [2026-07-10] — Archive Mode for Official Notices (migration 015)

**Implemented by:** Antigravity (AI Assistant)
**Session type:** Feature

**What was done:**
- Read all 17 `.ai/` documentation files before implementing
- Performed full root-cause analysis: expiry filter was present in 3 places (RLS, RPC, service layer)
- Created migration 015 to: (1) relax RLS policy, (2) update search_notices() RPC, (3) extend get_admin_stats() RPC
- Updated `services/notices.js`: added `isNoticeExpired()` helper, `activeOnly` param on `getRecentNotices()`, removed expiry filters from `getRecentNotices()` and `getRelatedNotices()`
- Updated `services/search.js`: mapped new `is_expired` and `expires_at` fields from search_notices RPC
- Rewrote `NoticeCard.jsx`: gray card background, archive banner stripe, Archive badge, expiry date footer; NO opacity reduction per design spec
- Rewrote `OfficialNoticesPage.jsx`: added Archive status pill filter (All / Active / Archive), updated sort order (pinned-active → active → pinned-archived → archived), added result count breakdown
- Updated `HomePage.jsx`: `getRecentNotices(6, true)` — home page still shows only active notices
- Updated `admin/DashboardPage.jsx`: added "Official Notices" stats section with Active, Archived, Draft stat cards

**Files created:**
- `supabase/migrations/015_expired_notices_visibility.sql`

**Files modified:**
- `frontend/src/services/notices.js`
- `frontend/src/services/search.js`
- `frontend/src/components/NoticeCard.jsx`
- `frontend/src/pages/OfficialNoticesPage.jsx`
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/pages/admin/DashboardPage.jsx`
- `CHANGELOG.md`
- `ROADMAP.md`
- `.ai/CHANGE_HISTORY.md` (this file)

**Migrations applied:**
- 015_expired_notices_visibility.sql — RLS update, search_notices() RPC, get_admin_stats() RPC

**Build status:** ✅ Pass (vite build — 116 modules, 17.48s)

**Notes:**
- Migration 015 must be applied manually in Supabase Dashboard → SQL Editor before deploying to production
- The `get_admin_stats()` RPC column additions are backward compatible; no callers broke
- The large bundle size warning (~636kB) is pre-existing and not related to this feature
- `NoticeDetailPage.jsx` required no changes — the expired banner at line 264 already existed and the RLS relaxation is the only requirement for detail pages to load archived notices
- `admin/OfficialNoticesPage.jsx` required no changes — admin already sees all notices via `notices_admin_all` RLS policy
