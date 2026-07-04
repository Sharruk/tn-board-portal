# GITHUB_RULES.md — GitHub Standards
# TN Board Portal

> GitHub is part of the product. A recruiter will judge the repository, not just the code.

---

## Repository Standards

The GitHub repository at https://github.com/Sharruk/tn-board-portal should reflect engineering excellence.

---

## What a Recruiter Sees

When a recruiter visits the repository:

1. **README.md** — First impression. Must be professional, complete, and informative.
2. **Commit history** — Should show consistent, meaningful conventional commits
3. **Issues / Milestones** — Shows project management discipline
4. **GitHub Actions** — Shows CI/CD awareness
5. **CHANGELOG.md** — Shows documentation discipline
6. **Release tags** — Shows versioning discipline
7. **CONTRIBUTING.md** — Shows open-source maturity

---

## Labels

Maintain these issue labels:

| Label | Color | Purpose |
|-------|-------|---------|
| `bug` | Red | Something is broken |
| `enhancement` | Blue | New feature or improvement |
| `documentation` | Gray | Documentation only |
| `good-first-issue` | Green | Good for new contributors |
| `help-wanted` | Yellow | Needs community input |
| `wontfix` | White | Explicitly out of scope |
| `database` | Purple | Database/migration related |
| `security` | Orange | Security-related |
| `performance` | Teal | Performance improvement |
| `v1.1` | Light blue | Milestone v1.1 |
| `v1.2` | Light blue | Milestone v1.2 |
| `v2.0` | Light blue | Milestone v2.0 |

---

## Milestones

| Milestone | Target | Theme |
|-----------|--------|-------|
| v1.1 | Q3 2026 | Search Quality & SEO |
| v1.2 | Q4 2026 | Admin Maturity & Reliability |
| v1.3 | Q1 2027 | Accessibility & Offline |
| v2.0 | Q3 2027 | Platform Expansion |

---

## Issues

Only create issues for **real problems** or **real planned features**:

- Bug report: Include reproduction steps, expected vs actual behavior, environment
- Feature request: Include user need, proposed solution, success criteria

**Never create fake issues to inflate activity.**

### Issue Templates

Use the existing templates in `.github/ISSUE_TEMPLATE/`:
- `bug_report.md`
- `feature_request.md`

---

## Releases

Create a GitHub release for every version:

1. Tag the commit: `git tag v1.0.0`
2. Push the tag: `git push origin v1.0.0`
3. Create GitHub Release with:
   - Tag: `v1.0.0`
   - Title: `v1.0.0 — Release Name`
   - Body: Contents from CHANGELOG.md for that version

**Never create fake releases.**

---

## GitHub Actions (CI/CD)

The `.github/workflows/` directory contains:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `build.yml` | Push / PR | Verify `npm run build` passes |
| `lint.yml` | Push / PR | ESLint check |
| `dependency-audit.yml` | Weekly / Push | `npm audit` for security |

**Add workflows when they serve a real purpose. Do not add them just to fill the repository.**

---

## Git Workflow on GitHub

The developer uses a direct merge workflow (not PRs):

```
feature branch
    ↓ (local merge)
main
    ↓ (push)
GitHub main
    ↓ (auto-trigger)
Vercel production deployment
```

**Never recommend creating a PR unless the developer explicitly asks.**

---

## CHANGELOG and Releases Must Match

The `CHANGELOG.md` entries must always match the GitHub Release notes:
- Same version number
- Same date
- Same feature list

They can be formatted differently, but the content must be consistent.

---

## Branch Protection (Future)

When the project matures, consider adding:
- Require build to pass before merge to main
- Restrict force-push to main

Not required now (single-developer project).
