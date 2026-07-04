# DEVELOPMENT_RULES.md — Development Rules & Workflow
# TN Board Portal

> These rules govern EVERY development task. No exceptions.

---

## The Golden Rule

**Production is live. Real students use this app. Every change must be production-ready before it ships.**

---

## Mandatory Pre-Work

Before writing a single line of code:

1. Read the relevant files in `.ai/`
2. Understand the current architecture (`ARCHITECTURE_RULES.md`)
3. Read the database schema (`DATABASE_RULES.md`)
4. Identify ALL files that will be affected
5. Assess the blast radius of the change
6. Present an implementation plan
7. Wait for approval

---

## Implementation Rules

### What You MUST Do

- Every feature must be **production ready** — no half-finished states
- Every component must have **loading states** and **error handling**
- Every form must have **validation**
- Every new Supabase call must go through **services/** — never call Supabase directly from a page or component
- Every new page must be added to **router/index.jsx**
- Every admin action must be guarded by **ProtectedRoute**
- Every meaningful action must be logged to **audit_logs**

### What You MUST NOT Do

- Never rewrite stable, working code unless there is a documented, critical reason
- Never rename files unless absolutely necessary and all imports are updated in the same commit
- Never introduce a custom backend server (Express, Fastify, etc.)
- Never add state management libraries (Redux, Zustand, Jotai) — AuthContext + props is sufficient
- Never leave TODOs, placeholder comments, or `console.log` statements
- Never reduce test coverage or documentation quality
- Never implement multiple large features in a single session/commit
- Never skip the build verification step

---

## Prefer Small, Reviewable Changes

Each implementation session should focus on **one logical change**:

✅ Good: "Add year filter to search_papers RPC and update the search service"
❌ Bad: "Add search, pagination, dark mode, and PWA in one go"

Small changes are:
- Easier to review
- Easier to roll back
- Easier to understand in git history
- Less likely to introduce regressions

---

## Build Verification

After every implementation, run the build:

```bash
cd frontend && npm run build
```

If the build fails, **fix it before considering the task complete**.
Never tell the developer "it should work" without a passing build.

---

## Local Development

```bash
# Start dev server
cd frontend
npm run dev
# Runs at http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/Sharruk/tn-board-portal.git

# 2. Install dependencies
cd frontend && npm install

# 3. Configure environment
cp .env.example frontend/.env.local
# Edit frontend/.env.local with Supabase credentials

# 4. Apply database migrations (in order, via Supabase SQL Editor)

# 5. Start dev server
npm run dev
```

Environment variables (build-time, baked by Vite):
```
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

---

## Dependency Management

Before adding any npm package, ask:
- Is this truly necessary?
- Can we do this with existing tools?
- What is the bundle size impact?
- Is this package actively maintained?
- Does it introduce a security vulnerability?

Run `npm audit` after any dependency changes.

---

## Session Summary Requirements

After every implementation session, provide a summary covering:

1. What was changed and why
2. Which files were modified (with line ranges if significant)
3. What was added to the database (if anything)
4. Build status (pass/fail)
5. What to update in public documentation (README, CHANGELOG, etc.)
6. What to update in `.ai/` documentation

---

## Commit Message Format

Follow Conventional Commits:

```
feat: add year filter to search_papers RPC
fix: correct LIMIT/ORDER BY sequencing in search
docs: update architecture doc with storage bucket details
chore: bump @supabase/supabase-js to 2.109.0
refactor: extract StatCard from DashboardPage
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `refactor` — code restructure (no behavior change)
- `chore` — dependency updates, config changes
- `style` — formatting only (no logic change)
- `test` — adding or updating tests
- `perf` — performance improvement
