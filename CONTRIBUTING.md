# Contributing to TN Board Portal

Thank you for your interest in contributing! This guide explains everything you need to get started, from cloning the repo to opening a pull request.

---

## Table of Contents

1. [Project Setup](#1-project-setup)
2. [Development Workflow](#2-development-workflow)
3. [Coding Standards](#3-coding-standards)
4. [Git Branch Strategy](#4-git-branch-strategy)
5. [Commit Message Conventions](#5-commit-message-conventions)
6. [Database Migrations](#6-database-migrations)
7. [Testing](#7-testing)
8. [Pull Request Checklist](#8-pull-request-checklist)

---

## 1. Project Setup

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Node.js | 20 LTS |
| npm | 10 |
| Git | 2.40 |
| Supabase CLI | 1.x (optional, for local dev) |

### Clone and Install

```bash
git clone https://github.com/Sharruk/tn-board-portal.git
cd tn-board-portal/frontend
npm install
```

### Environment Variables

Copy `.env.example` from the project root:

```bash
cp ../.env.example .env.local
```

Fill in your Supabase project URL and anon key:

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

> **Never commit `.env.local`.** It is listed in `.gitignore`.

### Start the Dev Server

```bash
npm run dev
```

The app runs at `http://localhost:5173`.

---

## 2. Development Workflow

```
main
 └── develop          ← integration branch (PRs merge here first)
      ├── feature/*   ← new features
      ├── fix/*        ← bug fixes
      ├── enhance/*   ← enhancements / refactoring
      ├── docs/*       ← documentation-only changes
      └── chore/*      ← dependency updates, config changes
```

1. Create a branch from `develop` (never from `main` directly).
2. Make your changes, writing clean, focused commits.
3. Push your branch and open a PR targeting `develop`.
4. After review and testing, the maintainer merges to `develop`.
5. Periodically, `develop` is merged to `main` for a production release.

---

## 3. Coding Standards

### JavaScript / React

- **ESM only** — all files use ES modules (`import`/`export`).
- **Functional components** — no class components.
- **Named exports** for components; default exports only for pages (React Router convention).
- **Props** — destructure at the function signature level.
- **No prop-types** — the project does not currently use TypeScript or prop-types; keep type intent clear through descriptive variable names and JSDoc comments where complex.
- Keep each component focused on a **single responsibility**; split if it grows beyond ~150 lines of JSX.

### CSS / Tailwind

- Use Tailwind utility classes in JSX; avoid inline `style` attributes except for genuinely dynamic values (e.g. computed widths).
- Group Tailwind classes in logical order: layout → spacing → typography → colour → interaction → responsive.
- Use the `cn()` utility (or `clsx`) for conditional class composition.

### Supabase / Data Access

- All Supabase calls belong in `frontend/src/services/*.js` — never call `supabase` directly from a page or component.
- Always handle the `{ data, error }` destructure pattern and propagate errors to the UI.
- Never expose the service role key to the frontend.

### File Naming

| Type | Convention | Example |
|------|-----------|---------|
| React components | PascalCase | `NoticeCard.jsx` |
| Pages | PascalCase + `Page` suffix | `SearchPage.jsx` |
| Services | camelCase | `notices.js` |
| Hooks | camelCase + `use` prefix | `useAuth.js` |
| Migrations | `NNN_description.sql` | `015_fts_search.sql` |

---

## 4. Git Branch Strategy

| Prefix | Use |
|--------|-----|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `enhance/` | UI/UX or code improvements that are not bugs |
| `docs/` | Documentation only |
| `chore/` | Dependency bumps, Vite config, CI tweaks |
| `migration/` | Supabase migration + corresponding frontend change |

**Example branch names:**

```
feature/full-text-search-upgrade
fix/search-rpc-limit-ordering
enhance/admin-dashboard-stat-card
docs/wiki-architecture
migration/015-fts-tsvector
```

---

## 5. Commit Message Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer: Closes #<issue-number>]
```

### Types

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `enhance` | Improvement to existing feature |
| `refactor` | Code restructure without behaviour change |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, config |
| `test` | Adding or updating tests |
| `perf` | Performance improvement |
| `security` | Security patch |
| `migration` | Database migration |

### Examples

```
feat(search): add year filter to search_papers RPC

migration(015): add tsvector column to papers for full-text search

fix(bulk-upload): surface duplicate row warning instead of silent skip

docs(wiki): add architecture overview page

chore(deps): bump @supabase/supabase-js to 2.110.0
```

---

## 6. Database Migrations

- Migrations live in `supabase/migrations/` and are numbered sequentially: `NNN_description.sql`.
- Every migration must be **idempotent** — use `IF NOT EXISTS`, `CREATE OR REPLACE`, and `ON CONFLICT DO NOTHING` everywhere.
- Never modify an already-merged migration file. Write a new migration instead.
- Test your migration against a clean Supabase project before opening a PR.
- Include `COMMENT ON TABLE` and `COMMENT ON COLUMN` for every new table and significant column.
- Update `supabase/README.md` with a one-line description of the new migration.

---

## 7. Testing

The project does not yet have an automated test suite. Until one is established:

- **Manually test all affected pages** in the browser before opening a PR.
- **Test both public and admin paths** if your change touches shared services or RPCs.
- **Test RPC changes** directly in the Supabase SQL Editor before migrating.
- For bulk-upload changes, test with at least 10 rows including a duplicate and a missing-field row.

When an automated test suite is introduced (tracked in #29), all PRs will require a passing test run in CI.

---

## 8. Pull Request Checklist

Before marking your PR as ready for review, confirm:

- [ ] Branch is based on `develop`, not `main`
- [ ] Branch name follows the `type/description` convention
- [ ] All commit messages follow Conventional Commits format
- [ ] Code runs locally with `npm run dev` without console errors
- [ ] `npm run build` completes without errors
- [ ] New UI components are tested across desktop and mobile viewports (Chrome, Firefox, Safari)
- [ ] All Supabase service calls handle the `error` object and surface it to the UI
- [ ] New database migrations are idempotent and include comments
- [ ] No `.env.local` or secrets committed
- [ ] PR description clearly states: what changed, why, and how to test it
- [ ] Related issue is referenced with `Closes #<issue-number>`

---

## Questions?

Open a [GitHub Discussion](https://github.com/Sharruk/tn-board-portal/discussions) in the **Q&A** category.
