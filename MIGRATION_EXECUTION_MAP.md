# Migration Execution Map
## Every File — Action, Reason, and Verified Against Actual Code

**Status:** Pre-migration audit. No code has been modified.  
**Verification method:** Every file listed was read from the actual codebase, not assumed.

---

## Discrepancies Found in Prior Analysis Documents

The following items in the prior analysis documents do not match the actual code. They are flagged and corrected here.

### ⚠ Discrepancy 1 — DashboardPage imports `adminApi` as default export
- **Analysis said:** "Update `DashboardPage.jsx` → call `getAdminStats()`"
- **Actual code (line 4, 80):**
  ```javascript
  import adminApi from '../../services/admin'          // default Axios instance import
  adminApi.get('/admin/stats')                          // inline call, not getAdminStats()
  ```
- **Correction:** `admin.js` exports the Axios instance as `default`. DashboardPage calls it directly. After migration, the default export must change from an Axios instance to an object with a `.get()` method OR the DashboardPage must be updated to call the named `getAdminStats()` export.

### ⚠ Discrepancy 2 — `audit_logs.timestamp` vs `created_at`
- **Analysis said:** `created_at` column exists in audit_logs
- **Backend ORM model (actual):** `timestamp = Column(DateTime, ...)` — column is named `timestamp`
- **Supabase migration 001_schema.sql (actual):** `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` — column is `created_at`
- **DashboardPage (actual, line 350):** `log.timestamp` — reads the backend's column name
- **Correction:** After migration, DashboardPage must read `log.created_at` instead of `log.timestamp`. This is a required frontend code change that was not listed in the analysis.

### ⚠ Discrepancy 3 — `audit_logs.target_details` type mismatch
- **Backend:** Stored as `Text` (JSON string). FastAPI returns it as a plain string. DashboardPage (line 333) does `JSON.parse(log.target_details)`.
- **Supabase schema:** `target_details JSONB`. PostgREST returns JSONB as a **parsed JavaScript object**, not a string. `JSON.parse(object)` → `JSON.parse("[object Object]")` → broken.
- **Correction:** After migration, DashboardPage must read `log.target_details` directly as an object without `JSON.parse()`. Change:
  ```javascript
  // BEFORE (current)
  const d = JSON.parse(log.target_details)
  // AFTER (post-migration)
  const d = log.target_details
  ```
  This change must be added to the frontend migration scope.

### ✅ Discrepancy 4 — Confirmed NOT a discrepancy: `ip_address`
- DashboardPage reads `log.ip_address` (line 347)
- Supabase 001_schema.sql line 99: `ip_address VARCHAR(45)` — column EXISTS in schema
- **Status: No fix required.** But after migration, the frontend will be responsible for passing the IP on login events (see note in AUTH_MIGRATION_PLAN about `login_success` / `login_failure` audit entries — those are currently logged server-side by FastAPI).

### ⚠ Discrepancy 5 — Upload progress callback
- **Analysis said:** "move upload to `supabase.storage.from('papers').upload(...)`"
- **Actual code:** `uploadPaper(fd, (pct) => setUploadProgress(pct))` — both `PapersPage` and `BulkUploadTab` pass a progress callback. The admin.js service currently uses `axios.post(..., { onUploadProgress: (e) => onProgress(Math.round(e.loaded * 100 / e.total)) })`
- **Supabase Storage SDK:** The `supabase.storage.from().upload()` method does **not** support upload progress callbacks. There is no equivalent to Axios `onUploadProgress`.
- **Correction:** Progress bars must be replaced with an indeterminate spinner during Supabase Storage uploads. The UI must be updated to remove the `uploadProgress` state or repurpose it as a boolean.

### ⚠ Discrepancy 6 — `login_success` / `login_failure` audit log entries
- **Analysis said:** Frontend inserts to audit_logs on upload/edit/delete
- **Not mentioned:** The backend currently logs `login_success`, `login_failure`, and `login_blocked` events to audit_logs. DashboardPage renders these with dedicated `ActionBadge` styles. After migration, these login events will NOT be auto-logged — Supabase Auth does not write to the application's `audit_logs` table.
- **Correction:** Either (a) log a `login_success` entry from the React LoginPage after successful `signInWithPassword`, or (b) accept that login events will no longer appear in audit logs. The `ip_address` field for login logs cannot be accurately obtained from the browser (can use a third-party IP API, but this adds complexity).

---

## Complete File Action List

### 🆕 CREATE — New files that must be created

| File | Reason |
|---|---|
| `frontend/src/lib/supabase.js` | Supabase client singleton. Single source of `createClient()`. |
| `frontend/.env.local` | Local development environment variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`. Never committed. |

---

### ✏️ REPLACE — Files replaced entirely (new content, same filename)

| File | Reason |
|---|---|
| `frontend/src/services/classes.js` | All Axios calls replaced by Supabase queries. Interface preserved. |
| `frontend/src/services/subjects.js` | All Axios calls replaced by Supabase queries. Interface preserved. |
| `frontend/src/services/papers.js` | All Axios calls replaced by Supabase queries. `getExamTypes()` becomes a hardcoded constant. |
| `frontend/src/services/search.js` | Axios call replaced by Supabase query + `search_queries` table insert. |
| `frontend/src/services/admin.js` | All Axios calls replaced. Default export (Axios instance) removed. All named exports replaced with Supabase equivalents. |
| `frontend/src/contexts/AuthContext.jsx` | JWT localStorage logic replaced with `supabase.auth.onAuthStateChange()`. |

---

### ✂️ MODIFY — Files that require targeted changes (not full replacement)

| File | Change Required | Reason |
|---|---|---|
| `frontend/src/pages/admin/DashboardPage.jsx` | (1) Remove `import adminApi from '../../services/admin'` and `adminApi.get('/admin/stats')` call — replace with `getAdminStats()`. (2) Change `log.timestamp` → `log.created_at` on line 350. (3) Change `JSON.parse(log.target_details)` → direct access `log.target_details`. | Three verified discrepancies require targeted fixes. |
| `frontend/src/pages/admin/LoginPage.jsx` | Replace `adminLogin(username, password)` call with `supabase.auth.signInWithPassword({ email, password })`. Change `username` field label to `Email`. | Auth system change. |
| `frontend/src/components/admin/ProtectedRoute.jsx` | `isAuthenticated` check continues to work IF `AuthContext` exports `isAuthenticated` in new implementation. Verify only — likely no change needed. | Defensive verification. |
| `frontend/src/pages/admin/PapersPage.jsx` | (1) Replace `uploadPaper(fd, progressCallback)` — remove progress callback, use indeterminate spinner. (2) Update error handling: `err.response?.data?.detail` → `err.message`. | Upload progress API change; Axios vs Supabase error format. |
| `frontend/src/pages/admin/BulkUploadTab.jsx` | Same as PapersPage: remove `onUploadProgress` progress tracking. All `err.response?.data?.detail` → `err.message`. | Same reasons. |
| `frontend/src/hooks/useFetch.js` | Update error extraction: `err.response?.data?.detail` → `err.message`. | Supabase errors don't have `.response.data.detail`. |
| `frontend/vite.config.js` | Remove the `proxy` block (`/api` and `/uploads` proxies). | No backend to proxy to. |
| `frontend/vercel.json` | Replace current content with single SPA rewrite: `{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }`. | Current file has placeholder `REPLACE_WITH_RAILWAY_URL`. |

---

### 🔒 KEEP — Files that need no changes

| File | Reason |
|---|---|
| `frontend/src/pages/HomePage.jsx` | All data from `getClasses()`, `getRecentPapers()`, `getPopularPapers()` — service interfaces preserved. |
| `frontend/src/pages/ClassPage.jsx` | Uses `getClass()`, `getSubjectsForClass()` — interface preserved. |
| `frontend/src/pages/SubjectPage.jsx` | Uses `getSubject()`, `getPapersForSubject()` — interface preserved. |
| `frontend/src/pages/PaperListPage.jsx` | Uses subject/paper services — interface preserved. |
| `frontend/src/pages/PaperDetailPage.jsx` | Uses `getPaperBySlug()`, `recordDownload()` — interface preserved. |
| `frontend/src/pages/SearchPage.jsx` | Uses `searchPapers()` — interface preserved. |
| `frontend/src/pages/NotFoundPage.jsx` | No data fetching. |
| `frontend/src/pages/admin/ContentStatusPage.jsx` | Uses `getContentStatus()` — interface preserved. |
| `frontend/src/components/Navbar.jsx` | No service calls. |
| `frontend/src/components/Footer.jsx` | No service calls. |
| `frontend/src/components/SearchBar.jsx` | No service calls. |
| `frontend/src/components/ClassCard.jsx` | Display only. |
| `frontend/src/components/PaperCard.jsx` | Display only. |
| `frontend/src/components/Breadcrumb.jsx` | Display only. |
| `frontend/src/components/LoadingSpinner.jsx` | Display only. |
| `frontend/src/components/adminErrorMessage.jsx` | Display only. |
| `frontend/src/components/AdminLayout.jsx` | Uses `useAuth()` for logout — must verify logout call works with new AuthContext. Likely no change. |
| `frontend/index.html` | No changes required. |
| `frontend/tailwind.config.js` | No changes required. |
| `frontend/postcss.config.js` | No changes required. |
| `frontend/package.json` | Add `@supabase/supabase-js`, optionally remove `axios`. |
| `supabase/migrations/001_schema.sql` | Already correct for target architecture. |
| `supabase/migrations/002_seed_data.sql` | Already correct. |
| `supabase/migrations/003_rls_policies.sql` | Already correct. |
| `supabase/migrations/004_functions.sql` | Already correct. |
| `supabase/migrations/005_search_analytics.sql` | Already correct. |
| `supabase/README.md` | Reference document, no changes. |

---

### 🗑️ DELETE — Files to remove after migration is verified

| File | Reason |
|---|---|
| `backend/app/api/admin.py` | No backend architecture. |
| `backend/app/api/auth.py` | Replaced by Supabase Auth. |
| `backend/app/api/classes.py` | Replaced by Supabase JS. |
| `backend/app/api/subjects.py` | Replaced by Supabase JS. |
| `backend/app/api/papers.py` | Replaced by Supabase JS. |
| `backend/app/api/__init__.py` | Part of backend. |
| `backend/app/models/models.py` | Replaced by Supabase schema. |
| `backend/app/schemas/schemas.py` | No backend; Supabase returns typed JSON directly. |
| `backend/app/services/auth.py` | Replaced by Supabase Auth. |
| `backend/app/services/storage.py` | Replaced by Supabase Storage SDK in frontend. |
| `backend/app/services/rate_limit.py` | Replaced by Supabase Auth built-in rate limiting. |
| `backend/app/services/audit.py` | Replaced by direct Supabase DB inserts from frontend. |
| `backend/app/services/analytics.py` | Replaced by `search_queries` table + RPC. |
| `backend/app/database.py` | No backend. |
| `backend/app/config.py` | No backend. |
| `backend/app/main.py` | No backend. |
| `backend/app/__init__.py` | No backend. |
| `backend/requirements.txt` | No backend. |
| `backend/Dockerfile` | No backend. |
| `backend/seed.py` | Replaced by 002_seed_data.sql. |
| `backend/migrate_41.py` | Migration helper, no longer needed. |
| `Procfile` | No backend server. Broken anyway (`gunicorn app:app` → no `app.py`). |
| `Dockerfile` (root) | No backend. |
| `docker-compose.yml` | No backend. |
| `change_admin_password.py` | Replaced by Supabase Auth dashboard. |
| `frontend/src/services/api.js` | Replaced by `frontend/src/lib/supabase.js`. |

---

## Summary Counts

| Action | Count |
|---|---|
| Create | 2 |
| Replace | 6 |
| Modify | 8 |
| Keep (unchanged) | 25+ |
| Delete | 25 |

**Total files changed (create + replace + modify):** 16  
**Total files deleted:** 25  
**Total files untouched:** 25+
