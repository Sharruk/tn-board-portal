# AGENTS.md — AI Operating Manual
# TN Board Portal

> **READ THIS FIRST.**
> This is the master operating manual for every AI coding assistant working on this repository.
> Do not make a single code change until you have read every file in this `.ai/` folder.

---

## What Is This Project?

TN Board Portal is a **production-quality, long-term software engineering portfolio project**.

It is NOT a college CRUD app.
It is NOT a throwaway prototype.
It IS a demonstration of real engineering — architecture, database design, security, documentation, and deployment — aimed at impressing recruiters at companies like Google, Microsoft, Atlassian, and GitHub.

**Every commit counts. Every decision matters. Every file you touch reflects on the developer.**

---

## Your Mandatory First Step

Before touching a single file, run through this checklist:

- [ ] Read `AGENTS.md` (this file)
- [ ] Read `PROJECT_CONTEXT.md`
- [ ] Read `ARCHITECTURE_RULES.md`
- [ ] Read `DATABASE_RULES.md`
- [ ] Read `CODING_STANDARDS.md`
- [ ] Read `DEVELOPMENT_RULES.md`
- [ ] Read the relevant workflow file (`FEATURE_WORKFLOW.md` or `BUG_FIX_WORKFLOW.md`)
- [ ] Read `DECISIONS.md` to understand past choices
- [ ] Read `CHANGE_HISTORY.md` to understand what already exists

---

## AI Workflow — Non-Negotiable Order

Every request, no exceptions:

```
1. Analyze the project (read relevant source files)
2. Understand architecture (read ARCHITECTURE_RULES.md)
3. Identify affected files
4. Explain the impact
5. Produce an implementation plan
6. WAIT FOR APPROVAL
7. Implement
8. Verify the build (npm run build)
9. Summarize changes
```

**Never skip step 6. Never implement without explicit approval.**

---

## Critical Constraints

| Rule | Reason |
|------|--------|
| Never rewrite stable, working modules | Production is live; regressions hurt real students |
| Never rename files unnecessarily | Breaks imports, git blame, and deployment |
| Never introduce a backend server | Frontend-only + Supabase is the intentional architecture |
| Never modify old migrations | Production data lives in those tables |
| Never leave TODOs or placeholder code | This is a portfolio project — quality is mandatory |
| Never invent completed work or fake GitHub activity | Portfolio integrity matters |
| Never add unnecessary dependencies | Every dep is a security surface and a bundle size cost |
| Never store secrets inside `.ai/` | The `.ai/` folder is now version-controlled — no API keys, passwords or tokens |

---

## Repository Visibility

- The repository is currently **private**.
- The `.ai/` folder is **intentionally version-controlled** during active development.
- The purpose is to synchronize AI memory across all development environments and AI coding assistants (Antigravity, Cursor, Replit, Codex, Claude Code, GitHub Copilot, and future assistants).
- Before making the repository **public** or sharing it with recruiters, review whether `.ai/` should remain in the repository or be moved to a separate private repository.
- **Never expose secrets, API keys, passwords, tokens, or credentials inside `.ai/`.** Every file in this folder may become public.

---

## What Is Committed vs. Not Committed

### Committed to Git (as of v1.0+)
- All `.ai/` files — AI operating manual, shared across all environments
- `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md`
- `docs/` — Architecture, Database, API, Deployment docs
- `frontend/src/**` — Application source code
- `supabase/migrations/**` — Database migrations

### Never Committed
- `.env.local`, `.env` — Files with real environment secrets
- `frontend/node_modules/`, `frontend/dist/` — Dependencies and build artifacts

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| UI Framework | React 18 |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS 3 |
| Routing | React Router DOM v6 |
| Backend-as-a-Service | Supabase |
| Database | PostgreSQL (via Supabase) |
| Auth | Supabase Auth (email/password) |
| Storage | Supabase Storage (3 buckets) |
| Hosting | Vercel (Vite SPA, global CDN) |

---

## Git Workflow

The developer does NOT use Pull Requests. Follow this exact workflow:

```
feature branch
    ↓ commit
    ↓ push feature/dev branch
    ↓ git checkout main
    ↓ git pull main
    ↓ git merge feature/dev
    ↓ git push main
```

**Never recommend PRs unless explicitly asked.**

---

## The `.ai/` Folder Is the Project's Permanent Memory

Every significant decision → update `DECISIONS.md`
Every new coding convention → update `CODING_STANDARDS.md`
Every workflow improvement → update `DEVELOPMENT_RULES.md`
Every roadmap change → update `PROJECT_CONTEXT.md`
Every implementation → update `CHANGE_HISTORY.md`

The `.ai/` folder is a living document. Keep it current.
