# GIT_WORKFLOW.md — Git Workflow
# TN Board Portal

> This is the developer's personal workflow. Follow it exactly. Never recommend PRs unless explicitly asked.

---

## The Workflow

```
1. Create / switch to feature branch
       git checkout -b feature/your-feature-name
       (or)
       git checkout feature/existing-branch

2. Make commits on the feature branch
       git add .
       git commit -m "feat: describe your change"

3. Push the feature branch
       git push origin feature/your-feature-name

4. Merge to main
       git checkout main
       git pull origin main
       git merge feature/your-feature-name
       git push origin main

5. Vercel auto-deploys from main
```

---

## Commit Message Format

Follow Conventional Commits exactly:

```
<type>: <short description>

[optional body]
[optional footer]
```

### Types

| Type | When to use |
|------|------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only change |
| `refactor` | Code change that is neither a fix nor a feature |
| `chore` | Dependency updates, config changes, build changes |
| `style` | Formatting, whitespace — no logic change |
| `test` | Adding or updating tests |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |

### Examples

```
feat: add year filter to search_papers RPC and search UI
fix: correct LIMIT/ORDER BY sequencing in search_papers()
docs: add ARCHITECTURE.md database schema section
refactor: extract StatCard from admin DashboardPage
chore: bump @supabase/supabase-js to 2.109.0
perf: add index on papers.year column
ci: add dependency audit GitHub Action
```

---

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/kebab-name` | `feature/search-tsvector` |
| Bug fix | `fix/kebab-name` | `fix/search-order-bug` |
| Hotfix | `hotfix/kebab-name` | `hotfix/rls-policy-fix` |
| Documentation | `docs/kebab-name` | `docs/architecture-update` |
| Database | `db/kebab-name` | `db/015-study-materials` |

---

## Important Rules

### NEVER
- Commit `.env.local` or any file containing secrets
- Store API keys, passwords, or tokens inside `.ai/` (the folder is now version-controlled)
- Force-push to `main`
- Recommend Pull Requests unless explicitly asked

### ALWAYS
- Verify the build passes before pushing to main
- Write a meaningful commit message
- Update public documentation as part of the commit (CHANGELOG, etc.)

---

## Commit What Belongs in Git

### ✅ Commit These
- `frontend/src/**` — Application source code
- `supabase/migrations/**` — New migration files
- `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md`
- `docs/**` — Architecture, API, Database docs
- `.github/**` — GitHub Actions, issue templates
- `vercel.json`, `.env.example`

### ❌ Never Commit These
- `.env.local`, `.env` — Environment variables with secrets
- `frontend/node_modules/` — Dependencies (in `.gitignore`)
- `frontend/dist/` — Build artifacts (in `.gitignore`)

---

## Vercel Deployment

Vercel watches the `main` branch. Every push to `main` triggers a production deployment automatically.

There is no staging environment currently. Test locally before merging to main.

Production URL: https://tn-board-portal.vercel.app

---

## GitHub Best Practices

The GitHub repository should reflect the quality of the project:

- **Issues** — Use for tracking real bugs and planned features
- **Labels** — bug, enhancement, documentation, help-wanted, good-first-issue
- **Milestones** — v1.1, v1.2, v1.3, v2.0
- **Releases** — Tag and create a release note for each version
- **CHANGELOG.md** — Keep synchronized with releases
- **Actions** — Build, lint, dependency audit

Never create fake issues, fake releases, or fake activity to inflate the repository.
