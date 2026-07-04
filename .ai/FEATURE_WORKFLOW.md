# FEATURE_WORKFLOW.md — Feature Implementation Workflow
# TN Board Portal

> Follow this exact workflow for every new feature. Do not skip steps.

---

## Step 1 — Understand the Request

Before anything else:

- What exactly is being built?
- Who uses it? (Student? Admin? Both?)
- What database tables are involved?
- What new tables/columns are needed?
- What existing services/components can be reused?
- What is the scope? (UI only? DB + UI? DB + Service + UI?)

---

## Step 2 — Read Relevant Documentation

- `ARCHITECTURE_RULES.md` — Understand the layer structure
- `DATABASE_RULES.md` — Understand schema and migration rules
- `CODING_STANDARDS.md` — Understand code conventions
- `DECISIONS.md` — Check if a similar decision was already made

---

## Step 3 — Identify Affected Files

List every file that will be created or modified:

```
New files:
- supabase/migrations/015_study_materials.sql
- src/services/studyMaterials.js
- src/pages/StudyMaterialsPage.jsx
- src/pages/admin/StudyMaterialsPage.jsx
- src/components/StudyMaterialCard.jsx

Modified files:
- src/router/index.jsx          — add new routes
- src/components/admin/AdminLayout.jsx  — add sidebar link
- CHANGELOG.md                  — document new feature
```

---

## Step 4 — Produce an Implementation Plan

Present the plan covering:

1. **Database changes** — New migration(s), tables, columns, RPCs, RLS
2. **Service layer** — New or updated service functions
3. **Component layer** — New or reused components
4. **Page layer** — New or updated pages
5. **Routing** — Router changes
6. **Admin changes** — Admin sidebar, admin pages
7. **Documentation** — CHANGELOG, ROADMAP, docs/ARCHITECTURE.md updates

---

## Step 5 — Wait for Approval

**Do not write a single line of implementation code until the plan is approved.**

---

## Step 6 — Implement in This Order

Always implement in dependency order:

```
1. Database migration (supabase/migrations/NNN_xxx.sql)
2. Service functions (src/services/xxx.js)
3. Reusable components (if needed)
4. Page components
5. Router updates
6. Admin sidebar update (if admin feature)
7. Documentation updates
```

---

## Step 7 — Verify the Build

```bash
cd frontend && npm run build
```

Build must pass before the task is considered complete.

---

## Step 8 — Update Documentation

After every feature implementation:

**Public docs (commit these):**
- `CHANGELOG.md` — Add to `[Unreleased]` section
- `ROADMAP.md` — Mark feature as complete if it was planned
- `docs/ARCHITECTURE.md` — Update if architecture changes

**Private docs (update `.ai/`):**
- `.ai/CHANGE_HISTORY.md` — Log the implementation
- `.ai/DECISIONS.md` — Log any new architectural decisions made
- `.ai/PROJECT_CONTEXT.md` — Update current modules list if needed

---

## Checklist Template

Copy this for every feature:

```
[ ] Step 1 — Understand the request
[ ] Step 2 — Read relevant .ai/ docs
[ ] Step 3 — List all affected files
[ ] Step 4 — Implementation plan produced
[ ] Step 5 — Approval received
[ ] Step 6a — Database migration written
[ ] Step 6b — Service functions written
[ ] Step 6c — Components written
[ ] Step 6d — Pages written
[ ] Step 6e — Router updated
[ ] Step 6f — Admin sidebar updated (if applicable)
[ ] Step 7 — Build passes (npm run build)
[ ] Step 8a — CHANGELOG.md updated
[ ] Step 8b — ROADMAP.md updated
[ ] Step 8c — docs/ARCHITECTURE.md updated (if architecture changed)
[ ] Step 8d — .ai/CHANGE_HISTORY.md updated
[ ] Step 8e — .ai/DECISIONS.md updated (if decisions made)
```

---

## Feature Branch Naming

```
feature/study-materials
feature/search-tsvector-upgrade
feature/dark-mode
feature/admin-pagination
feature/pwa-manifest
```

Always use `feature/` prefix, kebab-case description.
