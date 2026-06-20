# Go / No-Go Report
## TN State Board Learning Platform — FastAPI → React + Supabase + Vercel

**Date:** 2026-06-20  
**Based on:** Full codebase audit of all frontend pages, services, hooks, admin components, backend models, schemas, services, and all 5 Supabase migration files.

---

## Verdict: ✅ GO

The platform can realistically migrate to React + Supabase + Vercel without losing any critical functionality. The migration is well-scoped, the Supabase schema is already written correctly, and 25+ frontend files require zero changes.

---

## Complexity Estimates by Area

---

### 🟢 Authentication — LOW complexity

**Why LOW:**
- The current auth is straightforward JWT: login → check table → return token → attach to headers.
- Supabase Auth provides an identical flow with a single SDK method: `signInWithPassword()`.
- `AuthContext.jsx` is a clean, isolated context — no auth logic is scattered through other components.
- `ProtectedRoute.jsx` already checks a single boolean (`isAuthenticated`) — trivial to keep.
- The only real work is removing `localStorage.setItem('adminToken', ...)` and replacing it with `supabase.auth.onAuthStateChange()`.

**Risk:** The admin currently logs in with a `username` field. Supabase Auth requires `email`. The login form field must change label from "Username" to "Email" and the admin must know their email address.

**Estimated effort:** 2–3 hours.

---

### 🟢 Storage — LOW complexity

**Why LOW:**
- Supabase Storage is already the production backend. The bucket (`papers`) already exists. CDN URLs already work.
- The only change is who calls the Supabase Storage SDK: currently FastAPI calls it server-side; after migration, React calls it client-side.
- The `upload()` and `remove()` SDK methods are nearly identical to what `storage.py` already does.
- File validation (PDF only, max 50 MB) moves to the frontend — it's 5 lines of JavaScript.

**Risk:** Upload progress bars will become indeterminate spinners. The Supabase JS Storage SDK does not expose upload progress events. For a student portal with small-to-medium PDFs this is acceptable, but it is a UX regression for large files.

**Estimated effort:** 3–4 hours.

---

### 🟡 Search — MEDIUM complexity

**Why MEDIUM:**
- The current FastAPI search queries across 4 fields: `papers.title`, `papers.exam_type`, `subjects.name`, `classes.name` — with alias expansion (e.g., "maths" → "mathematics").
- Supabase PostgREST's `.or()` filter cannot span joined tables. Cross-join ILIKE requires a custom SQL function (RPC).
- Writing a `search_papers(q text)` PostgreSQL function is not complex, but it requires an additional migration file and careful testing.
- Alias expansion can remain client-side (as it is today in `search.js`).
- Analytics logging moves from in-memory to `search_queries` table insert — simpler and more durable.

**Risk:** If the RPC function is skipped and only `title` + `exam_type` ILIKE is implemented, students searching "maths" would not find subjects named "Mathematics" in the subject name field. This degrades discoverability.

**Recommendation:** Write a `search_papers(q text)` RPC. It is ~15 lines of SQL and eliminates the risk entirely.

**Estimated effort:** 4–6 hours (including RPC function + testing).

---

### 🟢 Analytics — LOW complexity

**Why LOW:**
- The current implementation stores search data in a Python `deque` in memory — it is lost on every restart or deployment. This is effectively broken in any production environment.
- The Supabase target (`search_queries` table + `get_search_analytics()` RPC) is strictly superior.
- The `get_search_analytics()` function already exists in `004_functions.sql`. The `search_queries` table and its indexes are in `005_search_analytics.sql`.
- The frontend change is: fire-and-forget `supabase.from('search_queries').insert({ term, result_count })` on every search.

**Estimated effort:** 1–2 hours.

---

### 🟡 Bulk Upload — MEDIUM complexity

**Why MEDIUM:**
- The bulk upload UI (`BulkUploadTab.jsx`) is sophisticated: filename parsing (`extractMetadata`), per-file form fields, duplicate detection, warning system, sequential upload loop.
- **All of this logic is 100% client-side and requires zero changes** — `extractMetadata`, `computeWarnings`, the form state machine, the sequential loop.
- The only changes are: (1) replace `uploadPaper()` internals with Supabase Storage + DB insert; (2) remove the per-file progress percentage (Supabase SDK limitation).
- The audit log entry for `bulk_upload` action must be inserted manually from the React service.

**Risk:** Sequential upload to Supabase Storage is slightly slower than to a local FastAPI endpoint (additional network hop). For batches of 20+ large PDFs, this may be noticeable. Not a correctness issue.

**Estimated effort:** 3–4 hours.

---

### 🟡 Admin Dashboard — MEDIUM complexity

**Why MEDIUM:**
- The dashboard aggregates 6 independent data sources in a single `Promise.allSettled()` call. After migration, all 6 sources become Supabase calls — this is fine.
- Three verified discrepancies require targeted fixes: (1) `adminApi.get('/admin/stats')` → `getAdminStats()`; (2) `log.timestamp` → `log.created_at`; (3) `JSON.parse(log.target_details)` → direct object access.
- The fixes are small (3 targeted edits) but they are not obvious without reading the code — they would cause silent bugs if missed.
- Login audit log entries (`login_success`, `login_failure`, `login_blocked`) will stop appearing. The dashboard shows these in the audit log with dedicated badge styles. This is a visible gap.

**Risk:** If the 3 discrepancy fixes are missed, the dashboard will either crash (JSONB parse error) or show wrong timestamps. These are high-priority fixes.

**Estimated effort:** 4–6 hours (including discrepancy fixes + audit log decision).

---

## Complete Risk Register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Admin cannot log in (uses username, not email) | High | High | Create Supabase Auth user with email address. Update login form label. |
| `log.timestamp` reads wrong column → wrong timestamps in audit log | High | Certain | Fix `log.timestamp` → `log.created_at` in DashboardPage (1 line). |
| `JSON.parse(JSONB object)` crashes audit log rendering | High | Certain | Remove `JSON.parse()` wrapper in DashboardPage (1 line). |
| Subject/class name search degraded | Medium | High | Write `search_papers()` RPC function in Supabase. |
| Login events missing from audit log | Medium | Certain | Accept gap OR log `login_success` from LoginPage after successful auth. |
| Upload progress bar lost | Low | Certain | Replace with indeterminate spinner — UX acceptable. |
| Large batch uploads slower | Low | Medium | Acceptable for a student portal. |
| `useFetch.js` error extraction broken | Low | High | Change `err.response?.data?.detail` → `err.message` (1 line). |

---

## What Becomes Easier After Migration

| Area | Current Pain | After Migration |
|---|---|---|
| Analytics | In-memory, lost on restart | Durable PostgreSQL table, cumulative |
| Deployments | Backend server must stay running | Zero-downtime static deploys, git-triggered |
| Secrets management | 7+ env vars, JWT secret to rotate | 2 env vars, no secret to rotate |
| Scaling | FastAPI process is single-threaded in dev | Supabase handles all DB/auth/storage scaling |
| Auth security | Manual JWT rotation, manual rate limiting | Supabase Auth handles all of this |
| PDF delivery | FastAPI proxies file URL response | Direct Supabase CDN — lower latency |
| Maintenance | Backend Python dependencies to update | No backend to maintain |

---

## What Is Hardest to Migrate

1. **Search cross-join filtering** — requires a custom PostgreSQL RPC function. Not hard to write, but requires careful testing. Easiest to get partially right and subtly wrong.

2. **Audit log login events** — login events were logged server-side by FastAPI using the request IP address. Reproducing this from the React frontend means: (a) calling an IP geolocation API to get the client IP, or (b) accepting that login events are logged without IP. No elegant solution.

3. **Upload progress percentage** — Supabase Storage SDK architecture does not expose progress events. There is no workaround using the current SDK version. An indeterminate spinner is the correct replacement.

---

## Prerequisites Before Starting Migration

All of these must be true before touching any frontend code:

- [ ] Supabase project created
- [ ] Supabase migrations 001–005 applied and verified (4 classes, 32 subjects, RLS active, RPC functions work)
- [ ] `papers` bucket created (Public, 50 MB, PDF MIME type)
- [ ] Storage RLS policies applied
- [ ] Admin user created in Supabase Auth (with email address, strong password, auto-confirmed)
- [ ] `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` available locally

---

## Final Recommendation

**Proceed with migration.** The architecture is sound, the schema is ready, and the scope is well-defined.

Prioritise in order:
1. Fix the 3 verified discrepancies in `DashboardPage.jsx` as part of the migration (not after).
2. Write the `search_papers()` RPC before wiring up the search service.
3. Replace upload progress bars with spinners proactively — do not leave Axios progress callbacks as dead code.
4. Decide explicitly whether login audit events are in scope. If yes, log from `LoginPage.jsx` after `signInWithPassword` succeeds.

**Estimated total migration time:** 6–10 hours of focused implementation work.  
**Expected monthly cost after migration:** $0 (Vercel free tier + Supabase free tier).  
**Expected maintenance overhead:** Zero backend operations.
