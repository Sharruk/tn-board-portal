# Phase 1 Verification Report
## TN State Board Learning Platform — Supabase Migration Foundation

**Date:** 2026-06-20  
**Auditor:** Full source read of all 5 migration files  
**Verdict: ✅ All files pass — one comment-level discrepancy noted (non-blocking)**

---

## 1. File Inventory

Every Phase 1 file is present and accounted for.

| # | File | Size | Status |
|---|------|------|--------|
| 1 | `supabase/migrations/001_schema.sql` | 129 lines | ✅ Exists |
| 2 | `supabase/migrations/002_seed_data.sql` | 82 lines | ✅ Exists |
| 3 | `supabase/migrations/003_rls_policies.sql` | 193 lines | ✅ Exists |
| 4 | `supabase/migrations/004_functions.sql` | 265 lines | ✅ Exists |
| 5 | `supabase/migrations/005_search_analytics.sql` | 82 lines | ✅ Exists |
| 6 | `supabase/README.md` | 182 lines | ✅ Exists |
| 7 | `MIGRATION_PLAN.md` | 267 lines | ✅ Exists |

---

## 2. Syntax Analysis — File by File

### `001_schema.sql` ✅ PASS

| Object | Type | Verdict | Notes |
|--------|------|---------|-------|
| `classes` | TABLE | ✅ Valid | `INTEGER PRIMARY KEY` — class number is PK by design |
| `subjects` | TABLE | ✅ Valid | FK → `classes(id) ON DELETE CASCADE` |
| `papers` | TABLE | ✅ Valid | `CHECK (paper_type IN ('question','answer_key'))` — enforced at DB level |
| `audit_logs` | TABLE | ✅ Valid | FK → `auth.users(id)` — correct Supabase schema reference |
| `search_queries` | TABLE | ✅ Valid | Replaces in-memory `analytics.py` |
| All `CREATE INDEX IF NOT EXISTS` | INDEX | ✅ Valid | 11 indexes total, all use safe `IF NOT EXISTS` |
| All `COMMENT ON` statements | COMMENT | ✅ Valid | 11 column/table comments |

**Dependency order within 001:** `classes` → `subjects` → `papers` → `audit_logs` → `search_queries`  
This order is correct in the file — tables are created in the right sequence for FK constraints.

**Confirmed idempotent:** All `CREATE TABLE IF NOT EXISTS` — safe to re-run.

---

### `002_seed_data.sql` ✅ PASS

Subject count verification (read directly from file):

| Class | Subjects seeded | Subjects listed |
|-------|-----------------|-----------------|
| Class 9 | 5 | Tamil, English, Mathematics, Science, Social Science |
| Class 10 | 5 | Tamil, English, Mathematics, Science, Social Science |
| Class 11 | 11 | Tamil, English, Maths, Physics, Chemistry, Biology, CS, CA, Acc, Commerce, Eco |
| Class 12 | 11 | Tamil, English, Maths, Physics, Chemistry, Biology, CS, CA, Acc, Commerce, Eco |
| **Total** | **32** | ✅ Matches `backend/seed.py` exactly |

**Confirmed idempotent:** All `INSERT … ON CONFLICT DO NOTHING` — safe to re-run.

**Cross-checked against `backend/seed.py`:** Every class ID, name, slug, subject name, subject slug, `is_practical`, and `display_order` value matches the Python source exactly.

---

### `003_rls_policies.sql` ✅ PASS (with one comment correction noted)

**RLS enabled on:** `classes`, `subjects`, `papers`, `audit_logs`, `search_queries` ✅

Policy inventory (read directly from file):

| Table | Policy Name | Command | Roles | USING clause |
|-------|-------------|---------|-------|--------------|
| classes | `classes_public_read` | SELECT | anon, authenticated | `true` |
| classes | `classes_admin_all` | ALL | authenticated | `auth.uid() IS NOT NULL` |
| subjects | `subjects_public_read` | SELECT | anon, authenticated | `true` |
| subjects | `subjects_admin_all` | ALL | authenticated | `auth.uid() IS NOT NULL` |
| papers | `papers_public_read` | SELECT | anon | `is_visible = true` |
| papers | `papers_admin_read` | SELECT | authenticated | `auth.uid() IS NOT NULL` |
| papers | `papers_admin_insert` | INSERT | authenticated | — |
| papers | `papers_admin_update` | UPDATE | authenticated | `auth.uid() IS NOT NULL` |
| papers | `papers_admin_delete` | DELETE | authenticated | `auth.uid() IS NOT NULL` |
| audit_logs | `audit_logs_admin_read` | SELECT | authenticated | `auth.uid() IS NOT NULL` |
| audit_logs | `audit_logs_admin_insert` | INSERT | authenticated | — |
| search_queries | `search_queries_public_insert` | INSERT | anon, authenticated | — |
| search_queries | `search_queries_admin_read` | SELECT | authenticated | `auth.uid() IS NOT NULL` |

**Total: 13 policies**

> ⚠️ **Comment discrepancy (non-blocking):** The verification comment at the bottom of `003_rls_policies.sql` says "Expected output: 12 policies." The correct number is **13**. The `papers` table has 5 policies (SELECT×2, INSERT, UPDATE, DELETE), not 4. The policies themselves are correct — only the expected count in the comment is wrong. Use `13` when verifying.

**Confirmed idempotent:** All policies preceded by `DROP POLICY IF EXISTS` — safe to re-run.

---

### `004_functions.sql` ✅ PASS

| Function | Returns | Security | Grantees | Verified |
|----------|---------|----------|----------|----------|
| `increment_download_count(INTEGER)` | void | SECURITY DEFINER | anon, authenticated | ✅ |
| `get_admin_stats()` | TABLE (7 BIGINT cols) | SECURITY DEFINER | authenticated | ✅ |
| `get_search_analytics()` | JSONB | SECURITY DEFINER | authenticated | ✅ |
| `get_content_status()` | JSONB | SECURITY DEFINER | authenticated | ✅ |

All functions include `SET search_path = public` — this is a required security hardening step for `SECURITY DEFINER` functions to prevent search path injection.

**`increment_download_count`:** Uses `IF NOT FOUND THEN RAISE EXCEPTION` — raises an error if the paper doesn't exist or isn't visible. The React service layer must catch this.

**`get_admin_stats`:** Returns a table with one row and 7 `BIGINT` columns. `COALESCE(SUM(download_count), 0)` handles the empty-table case correctly.

**`get_search_analytics`:** Uses `jsonb_agg(... ORDER BY ...)` — valid PostgreSQL aggregate syntax. `COALESCE(..., '[]'::JSONB)` handles empty tables correctly.

**`get_content_status`:** Nested loop over classes → subjects → exam types. The `FOREACH v_exam_type IN ARRAY` syntax is valid PL/pgSQL. Builds the exact JSON structure expected by `ContentStatusPage.jsx`.

---

### `005_search_analytics.sql` ✅ PASS

| Object | Type | Verdict | Notes |
|--------|------|---------|-------|
| `idx_search_queries_normalised_term` | INDEX | ✅ Valid | Functional index on `LOWER(TRIM(term))` — matches the GROUP BY in `get_search_analytics()` |
| `search_term_counts` | VIEW | ✅ Valid | `LIMIT 100` inside view definition — acceptable for a convenience query |
| `prune_old_search_queries(INTEGER)` | FUNCTION | ✅ Valid | `GET DIAGNOSTICS rows_deleted = ROW_COUNT` — correct PL/pgSQL syntax |

---

## 3. Exact Migration Execution Order

Run these in the Supabase SQL Editor in this exact sequence. Do not skip or reorder.

```
Step 1 → 001_schema.sql        (creates 5 tables + 11 indexes)
Step 2 → 002_seed_data.sql     (inserts 4 classes + 32 subjects)
Step 3 → 003_rls_policies.sql  (enables RLS, creates 13 policies)
Step 4 → 004_functions.sql     (creates 4 RPC functions + grants)
Step 5 → 005_search_analytics.sql (adds 1 index, 1 view, 1 maintenance function)
```

**Why this order is mandatory:**
- 001 must be first: all other files reference tables that 001 creates
- 002 must follow 001: inserts into tables that must already exist
- 003 must follow 001: `ALTER TABLE … ENABLE ROW LEVEL SECURITY` requires the table to exist
- 004 must follow 001: functions query `papers`, `subjects`, `classes`, `search_queries`
- 005 must follow 001 and 003: the index and view reference `search_queries` which 001 created; the view is read-only so it doesn't conflict with RLS

---

## 4. Supabase Setup Checklist

Complete these steps in the Supabase Dashboard before Phase 2 begins.

### A — Project Setup

- [ ] Go to [supabase.com](https://supabase.com) and sign in
- [ ] Click **New Project**
- [ ] Set project name: `tnboard` (or any name you choose)
- [ ] Set database password: generate a strong random password and save it in a password manager — you will need it if you ever connect with a DB client
- [ ] Select region: **ap-south-1** (Mumbai) — closest to Tamil Nadu students
- [ ] Click **Create new project**
- [ ] Wait for provisioning (~60 seconds — the loading bar must complete)

### B — Run SQL Migrations

- [ ] Click **SQL Editor** in the left sidebar
- [ ] Click **New query**
- [ ] Copy the entire contents of `001_schema.sql` → paste → click **Run**
- [ ] Confirm: success message, no red errors
- [ ] Click **New query** again (do not reuse the same tab)
- [ ] Copy the entire contents of `002_seed_data.sql` → paste → click **Run**
- [ ] Confirm: "Success. No rows returned"
- [ ] Run the verification query (see Section 6 below) — confirm `class_count=4`, `subject_count=32`
- [ ] Click **New query**
- [ ] Copy the entire contents of `003_rls_policies.sql` → paste → click **Run**
- [ ] Click **New query**
- [ ] Copy the entire contents of `004_functions.sql` → paste → click **Run**
- [ ] Click **New query**
- [ ] Copy the entire contents of `005_search_analytics.sql` → paste → click **Run**

### C — Create Admin User

- [ ] Click **Authentication** in the left sidebar
- [ ] Click **Users**
- [ ] Click **Add user** → **Create new user**
- [ ] Enter your admin email address (use a real email you control)
- [ ] Enter a strong password (minimum 12 characters, mix of uppercase, lowercase, numbers, symbols)
- [ ] Check **"Auto-confirm user"** — if this is not checked, the user will be in "Invited" state and login will fail
- [ ] Click **Create User**
- [ ] Confirm the user appears in the list with status "Active" (not "Invited")
- [ ] Copy the user's **UID** (the UUID shown in the users table) and save it

### D — Create Storage Bucket

- [ ] Click **Storage** in the left sidebar
- [ ] Click **New bucket**
- [ ] Enter name: `papers` — must be exactly this, lowercase, no spaces
- [ ] Toggle **Public bucket** to **ON** — required so students can view PDFs via direct URL
- [ ] (Optional) Set **File size limit**: `52428800` bytes = 50 MB
- [ ] (Optional) Set **Allowed MIME types**: `application/pdf`
- [ ] Click **Create bucket**
- [ ] Confirm the bucket `papers` appears in the list with a globe icon (public)

### E — Add Storage Bucket Policies

After creating the bucket, add 3 storage policies in **Storage → Policies → papers bucket**:

- [ ] Click **New policy** → **For full customization**

**Policy 1 — Public can download (SELECT):**
```sql
CREATE POLICY "papers_bucket_public_read"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'papers');
```

- [ ] Click **New policy** → **For full customization**

**Policy 2 — Admin can upload (INSERT):**
```sql
CREATE POLICY "papers_bucket_admin_insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

- [ ] Click **New policy** → **For full customization**

**Policy 3 — Admin can delete (DELETE):**
```sql
CREATE POLICY "papers_bucket_admin_delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

- [ ] Confirm all 3 storage policies appear in the list

### F — Collect API Keys

- [ ] Click **Settings** (gear icon) in the left sidebar
- [ ] Click **API**
- [ ] Copy and save in a password manager:
  - **Project URL** (e.g. `https://abcdefgh.supabase.co`)
  - **anon** key (long JWT starting with `eyJ…`)
  - **service_role** key (different long JWT — for admin scripts only, never in frontend)

---

## 5. Every Value to Collect from Supabase

Collect all of these before starting Phase 2. None can be retrieved again after being lost (except by going back to Settings → API).

| Value | Where to find it | Used in |
|-------|-----------------|---------|
| **Project URL** | Settings → API → Project URL | `VITE_SUPABASE_URL` env var |
| **anon key** | Settings → API → Project API keys → `anon public` | `VITE_SUPABASE_ANON_KEY` env var |
| **service_role key** | Settings → API → Project API keys → `service_role` | Admin scripts only — never in frontend |
| **Database password** | Set during project creation — not shown again | Direct DB connections (optional) |
| **Admin user UID** | Authentication → Users → UID column | Debugging / manual audit log queries |
| **Admin user email** | Authentication → Users | Login credentials for admin panel |

> ⚠️ The **service_role key** bypasses all RLS policies. Never add it to frontend code, `.env.local`, or any file committed to git. Store it only in a password manager.

---

## 6. Environment Variables Required After Migration

### Frontend (React + Vite)

These two variables are the **only** environment variables the React app needs.

| Variable | Required | Example Value | Where to set |
|----------|----------|---------------|-------------|
| `VITE_SUPABASE_URL` | ✅ Yes | `https://abcdefghijklmnop.supabase.co` | Vercel → Settings → Environment Variables |
| `VITE_SUPABASE_ANON_KEY` | ✅ Yes | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Vercel → Settings → Environment Variables |

For local development (Phase 2 testing in Replit), also create `frontend/.env.local`:
```
VITE_SUPABASE_URL=https://abcdefghijklmnop.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

> `.env.local` is already in `.gitignore` — it will not be committed.

### Variables No Longer Needed After Migration

These FastAPI variables are eliminated entirely when the backend is removed in Phase 4:

| Variable Eliminated | Was used for |
|--------------------|-------------|
| `DATABASE_URL` | SQLAlchemy connection |
| `JWT_SECRET_KEY` | PyJWT token signing |
| `CORS_ORIGINS` | FastAPI CORS middleware |
| `ENVIRONMENT` | FastAPI mode flag |
| `STORAGE_BACKEND` | Storage provider selection |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend Supabase client |
| `SUPABASE_BUCKET` | Backend bucket name |
| `JWT_EXPIRE_MINUTES` | Token expiry |
| `MAX_FILE_SIZE_MB` | Upload size cap |

---

## 7. Verification Queries

Run these in the Supabase SQL Editor after completing each setup step. Each query can be pasted directly and run.

### 7.1 — Verify Tables Exist (after 001)

```sql
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = t.table_name 
        AND table_schema = 'public') AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Expected output — 5 rows:**
```
audit_logs      |  8
classes         |  3
papers          | 12
search_queries  |  4
subjects        |  6
```

---

### 7.2 — Verify Seed Data (after 002)

```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
```

**Expected output:**
```
class_count | subject_count
------------+--------------
          4 |            32
```

Check class IDs are 9, 10, 11, 12 (not 1, 2, 3, 4):
```sql
SELECT id, name, slug FROM classes ORDER BY id;
```

**Expected output:**
```
 id |  name    | slug
----+----------+------
  9 | Class 9  | 9
 10 | Class 10 | 10
 11 | Class 11 | 11
 12 | Class 12 | 12
```

Check subjects per class:
```sql
SELECT c.name AS class, COUNT(s.id) AS subject_count
FROM classes c
JOIN subjects s ON s.class_id = c.id
GROUP BY c.name, c.id
ORDER BY c.id;
```

**Expected output:**
```
 class    | subject_count
----------+--------------
 Class 9  |  5
 Class 10 |  5
 Class 11 | 11
 Class 12 | 11
```

---

### 7.3 — Verify RLS Policies (after 003)

```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
```

**Expected output — exactly 13 rows:**
```
 tablename     | policyname                      | cmd    | roles
---------------+---------------------------------+--------+------------------------------
 audit_logs    | audit_logs_admin_insert         | INSERT | {authenticated}
 audit_logs    | audit_logs_admin_read           | SELECT | {authenticated}
 classes       | classes_admin_all               | ALL    | {authenticated}
 classes       | classes_public_read             | SELECT | {anon,authenticated}
 papers        | papers_admin_delete             | DELETE | {authenticated}
 papers        | papers_admin_insert             | INSERT | {authenticated}
 papers        | papers_admin_read               | SELECT | {authenticated}
 papers        | papers_admin_update             | UPDATE | {authenticated}
 papers        | papers_public_read              | SELECT | {anon}
 search_queries| search_queries_admin_read       | SELECT | {authenticated}
 search_queries| search_queries_public_insert    | INSERT | {anon,authenticated}
 subjects      | subjects_admin_all              | ALL    | {authenticated}
 subjects      | subjects_public_read            | SELECT | {anon,authenticated}
```

> Note: the migration file comment says "12 policies" but the correct count is **13**. This is a comment-only error; the policies themselves are all correct.

---

### 7.4 — Verify RLS Is Enforced (simulate anon access)

```sql
-- Temporarily disable the admin session to test as anon
-- Run this in a new SQL Editor window without being signed in as a service_role user
-- OR use the Supabase API Explorer with the anon key

-- Test 1: Anon can read classes (should return 4 rows)
SET LOCAL role TO anon;
SELECT COUNT(*) FROM classes;  -- expected: 4

-- Test 2: Anon can read visible papers only (0 papers since nothing uploaded yet)
SET LOCAL role TO anon;
SELECT COUNT(*) FROM papers;  -- expected: 0 (correct — no papers uploaded yet)

-- Test 3: Anon cannot read audit_logs (should return 0 or error)
SET LOCAL role TO anon;
SELECT COUNT(*) FROM audit_logs;  -- expected: 0 rows (RLS blocks all)

-- Test 4: Anon cannot read search_queries (should return 0 or error)
SET LOCAL role TO anon;
SELECT COUNT(*) FROM search_queries;  -- expected: 0 rows (RLS blocks SELECT)
```

> **Alternative (no SQL needed):** In the Supabase Dashboard, go to **Table Editor**. Switch the role to `anon` in the top-right dropdown. Navigate to `audit_logs` — you should see "0 rows" with no data visible.

---

### 7.5 — Verify RPC Functions Exist (after 004)

```sql
SELECT routine_name, routine_type, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_type = 'FUNCTION'
ORDER BY routine_name;
```

**Expected output — 4 functions (plus 1 from migration 005):**
```
 routine_name                  | routine_type | security_type
-------------------------------+--------------+---------------
 get_admin_stats               | FUNCTION     | DEFINER
 get_content_status            | FUNCTION     | DEFINER
 get_search_analytics          | FUNCTION     | DEFINER
 increment_download_count      | FUNCTION     | DEFINER
 prune_old_search_queries      | FUNCTION     | DEFINER   ← added by 005
```

---

### 7.6 — Verify `increment_download_count` Works

First insert a test paper, then call the function, then clean up.

```sql
-- Step 1: Insert a test paper
INSERT INTO papers (subject_id, exam_type, year, title, paper_type, is_visible)
VALUES (
  (SELECT id FROM subjects WHERE class_id = 9 AND slug = 'maths'),
  'Annual Exam',
  2024,
  'TEST PAPER — DELETE ME',
  'question',
  true
)
RETURNING id;
-- Note the returned id, e.g. 1

-- Step 2: Call the RPC function (use the id from above)
SELECT increment_download_count(1);  -- replace 1 with your actual id

-- Step 3: Verify count was incremented
SELECT id, title, download_count FROM papers WHERE title = 'TEST PAPER — DELETE ME';
-- Expected: download_count = 1

-- Step 4: Call again to confirm atomicity
SELECT increment_download_count(1);
SELECT id, title, download_count FROM papers WHERE title = 'TEST PAPER — DELETE ME';
-- Expected: download_count = 2

-- Step 5: Clean up
DELETE FROM papers WHERE title = 'TEST PAPER — DELETE ME';
```

---

### 7.7 — Verify Storage Bucket

```sql
-- Check bucket exists and is public
SELECT id, name, public, created_at
FROM storage.buckets
WHERE name = 'papers';
```

**Expected output:**
```
 id     | name   | public | created_at
--------+--------+--------+--------------------
 papers | papers | true   | 2026-xx-xx xx:xx:xx
```

Verify storage policies:
```sql
SELECT policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
ORDER BY policyname;
```

**Expected output — 3 rows:**
```
 policyname                    | cmd    | roles
-------------------------------+--------+------------------
 papers_bucket_admin_delete    | DELETE | {authenticated}
 papers_bucket_admin_insert    | INSERT | {authenticated}
 papers_bucket_public_read     | SELECT | {anon,authenticated}
```

---

### 7.8 — Verify Admin User

```sql
SELECT id, email, email_confirmed_at, created_at
FROM auth.users
ORDER BY created_at DESC
LIMIT 5;
```

**Expected output — 1 row:**
- `email` = your admin email
- `email_confirmed_at` = a timestamp (not NULL) — confirms the user is active

If `email_confirmed_at` is NULL, the user is in "Invited" state and login will fail. Fix:
```sql
UPDATE auth.users
SET email_confirmed_at = NOW()
WHERE email = 'your-admin-email@example.com';
```

---

## 8. Production-Ready Deployment Checklist

Complete every item before telling me to proceed with Phase 2.

### ✅ Database Foundation

- [ ] Migration 001 applied — 5 tables visible in Table Editor
- [ ] Migration 002 applied — 4 classes, 32 subjects confirmed
- [ ] Migration 003 applied — 13 RLS policies confirmed
- [ ] Migration 004 applied — 4 SECURITY DEFINER functions confirmed
- [ ] Migration 005 applied — `search_term_counts` view visible, `prune_old_search_queries` function exists
- [ ] Verification query 7.2 passes (class_count=4, subject_count=32)
- [ ] Verification query 7.3 passes (13 RLS policies)
- [ ] Verification query 7.5 passes (5 functions with DEFINER security)
- [ ] Verification query 7.6 passes (download count increments correctly)

### ✅ Authentication

- [ ] Admin user created in Supabase Auth
- [ ] Admin user status is **Active** (not "Invited")
- [ ] `email_confirmed_at` is NOT NULL (verified via query 7.8)
- [ ] Admin password saved in a password manager
- [ ] You can sign in at Supabase Dashboard → Authentication → Users and see your user

### ✅ Storage

- [ ] Bucket named exactly `papers` created
- [ ] Bucket is **Public** (globe icon visible in Storage list)
- [ ] 3 storage policies created (public read, admin insert, admin delete)
- [ ] Verification query 7.7 passes (bucket public=true, 3 policies)

### ✅ API Keys Collected

- [ ] **Project URL** saved (starts with `https://`, ends with `.supabase.co`)
- [ ] **anon key** saved (long JWT — safe to embed in frontend)
- [ ] **service_role key** saved in password manager only (never in code)
- [ ] Database password saved in password manager (needed for direct DB connections)

### ✅ Security

- [ ] service_role key is NOT in any file committed to git
- [ ] service_role key is NOT in `.env.local` or any env file
- [ ] Admin password is not `admin123` or any dictionary word
- [ ] Storage bucket policies created (without them, uploads silently fail)
- [ ] RLS is enabled on all 5 tables (verified via query 7.3)

### ✅ Pre-Phase 2 Gate

- [ ] All items above are checked
- [ ] Project URL and anon key are ready to be added to Replit Secrets or `.env.local`
- [ ] **Reply "approved" to proceed with Phase 2**

---

## Appendix — One-Shot Verification Query

Run this single query in the SQL Editor to get a dashboard of the entire setup state:

```sql
SELECT
  -- Tables
  (SELECT COUNT(*) FROM information_schema.tables
   WHERE table_schema = 'public' AND table_type = 'BASE TABLE')         AS table_count,       -- expected: 5

  -- Seed data
  (SELECT COUNT(*) FROM classes)                                         AS class_count,       -- expected: 4
  (SELECT COUNT(*) FROM subjects)                                        AS subject_count,     -- expected: 32

  -- RLS policies
  (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public')        AS rls_policy_count,  -- expected: 13

  -- Functions
  (SELECT COUNT(*) FROM information_schema.routines
   WHERE routine_schema = 'public' AND routine_type = 'FUNCTION')       AS function_count,    -- expected: 5

  -- Storage bucket
  (SELECT COUNT(*) FROM storage.buckets WHERE name = 'papers')          AS bucket_exists,     -- expected: 1

  -- Storage policies
  (SELECT COUNT(*) FROM pg_policies
   WHERE schemaname = 'storage' AND tablename = 'objects')              AS storage_policy_count, -- expected: 3

  -- Admin user
  (SELECT COUNT(*) FROM auth.users
   WHERE email_confirmed_at IS NOT NULL)                                 AS confirmed_users;   -- expected: 1
```

**All-green output:**
```
 table_count | class_count | subject_count | rls_policy_count | function_count | bucket_exists | storage_policy_count | confirmed_users
-------------+-------------+---------------+------------------+----------------+---------------+----------------------+----------------
           5 |           4 |            32 |               13 |              5 |             1 |                    3 |              1
```

If any column shows a different number, refer to the corresponding section above to find and fix the issue before proceeding to Phase 2.
