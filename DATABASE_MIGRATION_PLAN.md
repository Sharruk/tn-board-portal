# Database Migration Plan
## TN State Board Learning Platform — FastAPI → Supabase

---

## Table Disposition

| Table | Disposition | Reason |
|---|---|---|
| `classes` | ✅ Keep as-is | Static reference data, unchanged |
| `subjects` | ✅ Keep as-is | Static reference data, unchanged |
| `papers` | ✅ Keep, minor cleanup | Core content table; remove unused columns |
| `admins` | 🗑️ Remove | Replaced by `auth.users` (Supabase Auth) |
| `audit_logs` | ✅ Keep, modify FK | Change `admin_id` FK from `admins` → `auth.users` |
| `search_queries` | ✅ Keep as-is | Replaces in-memory analytics.py |

---

## Column-Level Changes

### `papers` table — Remove `file_path` column
| Column | Keep? | Reason |
|---|---|---|
| `id` | ✅ | Primary key |
| `subject_id` | ✅ | FK to subjects |
| `exam_type` | ✅ | Core metadata |
| `year` | ✅ | Core metadata |
| `title` | ✅ | Core metadata |
| `paper_type` | ✅ | `question` / `answer_key` |
| `file_path` | ⚠️ Keep for now | Used internally for storage deletion; can deprecate later once all deletes use Supabase Storage SDK directly via stored filename in `public_url` |
| `public_url` | ✅ | CDN URL served to browser |
| `youtube_url` | ✅ | Optional video embed |
| `is_visible` | ✅ | Visibility toggle |
| `download_count` | ✅ | Used by popular papers sort |
| `created_at` | ✅ | Used by recent papers sort |

> **Recommendation:** Keep `file_path` for now. It stores the storage object key (UUID.pdf) needed for deletion. Once migration is stable, it can be derived from `public_url` and the column removed.

### `audit_logs` table — Change FK target
| Column | Change |
|---|---|
| `admin_id` | Change FK from `admins(id)` → `auth.users(id)` |
| `admin_email` | Keep — denormalized copy, essential after user deletion |
| All other columns | No change |

### `admins` table — Drop entirely
This table is fully replaced by Supabase Auth (`auth.users`). The `username` concept becomes `email` in Supabase Auth. `password_hash`, `failed_login_count`, `locked_until` are all managed by Supabase Auth internally.

---

## Optimized Target Schema

The Supabase schema is already defined in `supabase/migrations/001_schema.sql` and is correct for the target architecture. The `audit_logs.admin_id` already references `auth.users(id)` in that file — it was designed for this exact migration.

**No new schema SQL is required.** The existing migration files (`001`–`005`) are the target schema.

---

## Migration Execution Plan

### Step 1 — Apply migrations to a fresh Supabase project (if not already done)
Run in the Supabase SQL Editor in order:

```sql
-- Run 001_schema.sql
-- Run 002_seed_data.sql
-- Run 003_rls_policies.sql
-- Run 004_functions.sql
-- Run 005_search_analytics.sql
```

### Step 2 — Verify seed data
```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,   -- must be 4
  (SELECT COUNT(*) FROM subjects) AS subject_count; -- must be 32
```

### Step 3 — Migrate existing papers (if any exist in the current DB)

If papers have been uploaded to the current Replit PostgreSQL database, export and re-import them:

```sql
-- On the source (Replit DB) — export papers as INSERT statements
COPY (
  SELECT id, subject_id, exam_type, year, title, paper_type,
         file_path, public_url, youtube_url, is_visible,
         download_count, created_at
  FROM papers
  ORDER BY id
) TO STDOUT WITH CSV HEADER;
```

Then import to Supabase SQL Editor:
```sql
INSERT INTO papers (id, subject_id, exam_type, year, title, paper_type,
                    file_path, public_url, youtube_url, is_visible,
                    download_count, created_at)
VALUES (...) ON CONFLICT (id) DO NOTHING;

-- Reset sequence after bulk insert
SELECT setval('papers_id_seq', (SELECT MAX(id) FROM papers));
```

> Note: PDF files themselves live in Supabase Storage and are already there if `STORAGE_BACKEND=supabase` was used. Only the metadata rows need migrating.

### Step 4 — Drop the `admins` table (after Supabase Auth admin is created)
```sql
-- Only run this AFTER verifying Supabase Auth admin login works
DROP TABLE IF EXISTS admins CASCADE;
```

### Step 5 — Verify RLS policies are active
```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
-- Expected: 12 policies across 5 tables
```

### Step 6 — Verify RPC functions are callable
```sql
-- From SQL Editor (simulates authenticated call)
SELECT * FROM get_admin_stats();

-- Expected: one row with total_papers, total_downloads, etc.
```

---

## Key RLS Rules (Summary)

| Table | Public (anon) | Admin (authenticated) |
|---|---|---|
| `classes` | SELECT all | ALL |
| `subjects` | SELECT all | ALL |
| `papers` | SELECT where `is_visible = true` | SELECT all + INSERT + UPDATE + DELETE |
| `audit_logs` | No access | SELECT + INSERT |
| `search_queries` | INSERT only | SELECT all |

---

## No Breaking Changes to Existing Data

- All `public_url` values in `papers` are Supabase Storage CDN URLs — they continue to work unchanged
- All `file_path` values (storage object keys) remain valid for deletion via Supabase Storage SDK
- The `search_queries` table accumulates data going forward — no historical data to migrate
