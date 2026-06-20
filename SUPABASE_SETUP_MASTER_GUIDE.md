# Supabase Setup Master Guide
## TN State Board Learning Platform

**Project URL:** https://fcxvrsgcvmlowehpilvr.supabase.co  
**Time required:** ~15–20 minutes  
**SQL Editor:** https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new

---

## How to use this guide

1. Open the [Supabase SQL Editor](https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new)
2. For each SQL step: paste the SQL, click **Run**, check for errors
3. After each step: paste the **Verification query**, click **Run**, confirm the expected result
4. Continue to the next step only after verification passes

---

## STEP 1 — Run `001_schema.sql`

**What it does:** Creates all 5 tables and their indexes.

**SQL file:** `supabase/migrations/001_schema.sql`

**Expected result after running:**
- Table `classes` created
- Table `subjects` created
- Table `papers` created
- Table `audit_logs` created
- Table `search_queries` created
- 12 indexes created

**Verification query:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Expected rows:**
```
audit_logs
classes
papers
search_queries
subjects
```
Must return exactly these 5 rows. If any are missing, re-run the schema SQL.

---

## STEP 2 — Run `002_seed_data.sql`

**What it does:** Inserts 4 classes (9, 10, 11, 12) and 32 subjects across all classes.

**SQL file:** `supabase/migrations/002_seed_data.sql`

**Expected result after running:**
- 4 rows in `classes`
- 32 rows in `subjects`

**Verification query:**
```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
```

**Expected result:**
```
class_count | subject_count
------------+--------------
          4 |            32
```

**Secondary verification — confirm class names:**
```sql
SELECT id, name, slug FROM classes ORDER BY id;
```
Expected: rows for Class 9, Class 10, Class 11, Class 12.

---

## STEP 3 — Run `003_rls_policies.sql`

**What it does:** Enables Row Level Security on all 5 tables and creates 13 access policies.

**SQL file:** `supabase/migrations/003_rls_policies.sql`

**Expected result after running:**
- RLS enabled on all 5 tables
- 13 policies created across 5 tables

**Verification query:**
```sql
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
```

**Expected:** 13 rows total across `classes`, `subjects`, `papers`, `audit_logs`, `search_queries`.

**Secondary check — confirm RLS is enabled:**
```sql
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN ('classes','subjects','papers','audit_logs','search_queries')
  AND relnamespace = 'public'::regnamespace
ORDER BY relname;
```
Expected: `relrowsecurity = true` for all 5 tables.

---

## STEP 4 — Run `004_functions.sql`

**What it does:** Creates 4 SECURITY DEFINER RPC functions called by the frontend, plus GRANT statements.

**SQL file:** `supabase/migrations/004_functions.sql`

**Functions created:**
- `increment_download_count(paper_id_param INTEGER)` — increments download counter
- `get_admin_stats()` — returns 7 aggregate stats
- `get_search_analytics()` — returns popular + recent searches as JSONB
- `get_content_status()` — returns coverage matrix as JSONB

**Expected result after running:**
- 4 functions created in `public` schema
- GRANT statements executed for `anon` and `authenticated` roles

**Verification query:**
```sql
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
```

**Expected rows (after this step — more will be added in steps 5 and 6):**
```
get_admin_stats       | FUNCTION
get_content_status    | FUNCTION
get_search_analytics  | FUNCTION
increment_download_count | FUNCTION
```

**Functional test:**
```sql
SELECT * FROM get_admin_stats();
```
Expected: 1 row with `total_classes = 4`, `total_subjects = 32`, all paper counts = 0.

---

## STEP 5 — Run `005_search_analytics.sql`

**What it does:** Adds a performance index, a convenience view, and a cleanup function.

**SQL file:** `supabase/migrations/005_search_analytics.sql`

**Objects created:**
- Index `idx_search_queries_normalised_term` on `search_queries`
- View `search_term_counts` — top 100 search terms by frequency
- Function `prune_old_search_queries(older_than_days INTEGER)` — retention cleanup

**Verification query:**
```sql
-- Check view exists
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public';
```
Expected: `search_term_counts`

```sql
-- Check prune function exists
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'prune_old_search_queries';
```
Expected: 1 row.

---

## STEP 6 — Run `006_search_rpc.sql`

**What it does:** Creates the `search_papers()` function used by the search page to do cross-table full-text search.

**SQL file:** `supabase/migrations/006_search_rpc.sql`

**Function created:**
- `search_papers(q TEXT, p_class_id INTEGER, p_exam_type TEXT, p_paper_type TEXT)` — searches across paper title, exam_type, subject name, class name using ILIKE

**Verification query:**
```sql
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'search_papers';
```
Expected: 1 row.

**Functional test:**
```sql
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
```
Expected: 0 rows returned, **no error**. (Empty result is correct — no papers uploaded yet.)

**Full function inventory after all 6 migrations:**
```sql
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
```
Expected — exactly 6 functions:
```
get_admin_stats
get_content_status
get_search_analytics
increment_download_count
prune_old_search_queries
search_papers
```

---

## STEP 7 — Create Storage Bucket

**Where:** Supabase Dashboard → [Storage](https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/storage/buckets) → **New bucket**

**Settings to enter:**

| Field | Value |
|---|---|
| **Name** | `papers` |
| **Public bucket** | ✅ ON (toggle enabled) |
| **File size limit** | `52428800` (= 50 MB) |
| **Allowed MIME types** | `application/pdf` |

Click **Create bucket**.

**Then add Storage RLS policies** — go to Storage → Policies → select the `papers` bucket → New policy:

Run this in the SQL Editor:
```sql
-- Allow public downloads
CREATE POLICY "papers_bucket_public_read"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'papers');

-- Allow admin uploads
CREATE POLICY "papers_bucket_admin_insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'papers' AND auth.uid() IS NOT NULL);

-- Allow admin deletions
CREATE POLICY "papers_bucket_admin_delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

**Verification:** Go to Storage → Buckets. Confirm `papers` appears with a globe icon (public).

---

## STEP 8 — Create Admin User

**Where:** Supabase Dashboard → [Authentication → Users](https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/auth/users) → **Add user** → **Create new user**

**Fields to fill:**

| Field | Value |
|---|---|
| **Email** | Your admin email (e.g. `admin@yourdomain.com`) |
| **Password** | Strong password — minimum 12 characters, mix letters/numbers/symbols |
| **Auto Confirm User** | ✅ Check this box |

Click **Create User**.

> **Important:** Check **"Auto Confirm User"**. Without this, the user will need to click an email verification link before they can log in.

**Verification:** The user appears in the Users table with `Confirmed` status.

---

## STEP 9 — Final Verification Checklist

After all steps above, confirm the application is fully operational.

### Database final check
```sql
-- All 5 tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
-- Expected: 5 rows

-- All 6 functions
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public' ORDER BY routine_name;
-- Expected: 6 rows

-- 13 RLS policies
SELECT COUNT(*) AS policy_count FROM pg_policies
WHERE schemaname = 'public';
-- Expected: 13

-- 1 view
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- Expected: search_term_counts

-- Seed data
SELECT (SELECT COUNT(*) FROM classes) AS classes,
       (SELECT COUNT(*) FROM subjects) AS subjects;
-- Expected: 4, 32

-- Stats function
SELECT * FROM get_admin_stats();
-- Expected: 1 row, total_classes=4, total_subjects=32

-- Search function
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
-- Expected: 0 rows, no error
```

### App feature verification

Open the app in browser and confirm:

| Feature | How to test | Expected |
|---|---|---|
| **Homepage** | Visit `/` | 4 class cards appear (Class 9, 10, 11, 12) |
| **Class page** | Click any class | List of subjects appears |
| **Subject page** | Click any subject | "No papers" empty state (correct — none uploaded yet) |
| **Search** | Type "maths" in search bar | Returns empty results (no papers yet) — no error |
| **Admin login** | Visit `/admin/login` | Enter email + password → redirects to dashboard |
| **Dashboard stats** | Admin → Dashboard | Shows 4 classes, 32 subjects, 0 papers |
| **Content status** | Admin → Content Status | Grid of classes/subjects appears |
| **Upload** | Admin → Papers → Upload | Upload form appears; upload a test PDF |
| **Bulk upload** | Admin → Papers → Bulk Upload | Bulk upload interface appears |
| **After upload** | Visit homepage | Uploaded paper appears in "Recently Added" |
| **Download** | Click a paper | PDF opens; download count increments |
| **Search (with data)** | Search for uploaded paper | Result appears |

---

## Quick Reference — Supabase Dashboard Links

| Action | Link |
|---|---|
| SQL Editor | https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new |
| Storage | https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/storage/buckets |
| Authentication | https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/auth/users |
| Table Editor | https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/editor |
| API Settings | https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/settings/api |
