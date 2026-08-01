# BUG_FIX_WORKFLOW.md — Bug Fix Workflow
# TN Board Portal

> Never immediately modify code. Always identify the root cause first.

---

## Step 1 — Understand the Bug Report

Before anything else, gather:

- **What is the observed behavior?** (what the user sees)
- **What is the expected behavior?** (what should happen)
- **How to reproduce it?** (exact steps)
- **Where does it happen?** (which page, which action)
- **When did it start?** (always broken, or regression?)
- **Browser/OS?** (if relevant)

---

## Step 2 — Identify the Root Cause Layer

Before touching code, determine where the bug lives:

| Layer | Indicators |
|-------|-----------|
| **Frontend (React)** | Wrong UI rendering, state not updating, broken navigation |
| **Service layer** | Wrong data returned, missing filters, wrong query |
| **Database (schema)** | Missing column, wrong data type, constraint violation |
| **RLS policy** | Data returns empty/403 for the wrong role |
| **RPC function** | Wrong logic in PostgreSQL function |
| **Supabase Storage** | Upload fails, file not accessible, wrong bucket |
| **Supabase Auth** | Session not persisting, login fails, admin guard not working |
| **Deployment (Vercel)** | Works locally but fails on production |
| **Browser limitation** | Works in Chrome, fails in Safari |
| **Architecture** | Fundamental design issue requiring a different approach |

---

## Step 3 — Reproduce It

Before proposing a fix, confirm you understand the bug:

- Read the relevant service file
- Read the relevant page/component
- Read the relevant migration (if DB-related)
- Trace the data flow from user action → service → Supabase → render

---

## Step 4 — Propose a Fix

State clearly:

1. **Root cause:** "The `search_papers` RPC applies LIMIT before ORDER BY, causing incorrect results"
2. **Affected file(s):** `supabase/migrations/015_fix_search_order.sql`, `services/search.js`
3. **Fix approach:** "Create migration 015 to fix the RPC; no service layer change needed"
4. **Risk assessment:** Low / Medium / High (explain if medium/high)

---

## Step 5 — Wait for Approval

Especially for:
- Database migrations (irreversible in production)
- Changes to RLS policies (security impact)
- Changes to service functions used across multiple pages

---

## Step 6 — Implement the Fix

Apply the fix in the correct layer.

If the fix requires a **database migration:**
- Follow `DATABASE_RULES.md` strictly
- New migration file: `015_fix_xxx.sql`
- Never edit existing migrations

If the fix is in a **service file:**
- Keep the function signature if other callers exist
- Add tests (manual, since no automated tests currently)

If the fix is in a **component or page:**
- Keep the same component structure
- Do not refactor unrelated parts while fixing

---

## Step 7 — Verify

1. Build passes: `cd frontend && npm run build`
2. Manually test the specific bug scenario
3. Verify no regressions on related pages/features

---

## Step 8 — Document

**CHANGELOG.md** — Add to `[Unreleased] → Fixed`:
```markdown
### Fixed
- `search_papers()` LIMIT applied before ORDER BY — corrected in migration 015
```

**.ai/CHANGE_HISTORY.md** — Log the bug and fix with date.

---

## Common Bug Patterns in This Project

### "Data not showing on the public page"
→ Check RLS: is the row's status = 'published'?
→ Check the service: is the `.eq('status', 'published')` filter applied?

### "Admin can't see data"
→ Check if the user is authenticated (check AuthContext)
→ Check if the RLS policy for `authenticated` role is correct

### "Upload succeeds but file not accessible"
→ Check bucket visibility (should be public)
→ Check the public_url stored in the DB (verify it matches the actual bucket URL)

### "Search returns no results"
→ Check RPC function logic (is ILIKE pattern `%term%` correct?)
→ Check if data has `status = 'published'` and is visible

### "Admin action not logged"
→ Check service function: is `audit_logs` insert happening?
→ Check RLS on audit_logs for `authenticated` role

### "Works locally but 404 on Vercel"
→ Check `vercel.json` — the SPA rewrite `/* → /index.html` must be present
→ Ensure the route is defined in `router/index.jsx`

### "Build fails on Vercel but passes locally"
→ Check env vars in Vercel Dashboard (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)
→ Check for case-sensitive import paths (Linux ≠ Windows)
