# Supabase Migration Status
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Evidence source:** Live app behaviour (classes + subjects load; RPC functions return 404)

---

## Summary

| Migration | File | Status | Confidence |
|---|---|---|---|
| 001 | `001_schema.sql` | ✅ Applied | High — tables exist, data loads |
| 002 | `002_seed_data.sql` | ✅ Applied | High — 4 classes, 32 subjects confirmed |
| 003 | `003_rls_policies.sql` | ✅ Likely applied | Medium — anon read working; confirm with verification query below |
| 004 | `004_functions.sql` | ❌ Not applied | High — all 5 functions return 404 |
| 005 | `005_search_analytics.sql` | ❌ Not applied | High — depends on 004; view not present |
| 006 | `006_search_rpc.sql` | ❌ Not applied | High — `search_papers` returns 404 |

---

## Migration Detail

### 001 — Schema `✅ Applied`

**File:** `supabase/migrations/001_schema.sql`  
**Dependencies:** none

**Objects created:**

| Object | Type | Status |
|---|---|---|
| `classes` | Table | ✅ Exists |
| `subjects` | Table | ✅ Exists |
| `papers` | Table | ✅ Exists (empty — no papers uploaded yet) |
| `audit_logs` | Table | ✅ Exists |
| `search_queries` | Table | ✅ Exists |
| `idx_classes_slug` | Index | ✅ Created with table |
| `idx_subjects_class_id` | Index | ✅ Created with table |
| `idx_papers_*` (6 indexes) | Index | ✅ Created with table |
| `idx_audit_logs_*` (3 indexes) | Index | ✅ Created with table |
| `idx_search_queries_*` (2 indexes) | Index | ✅ Created with table |

---

### 002 — Seed Data `✅ Applied`

**File:** `supabase/migrations/002_seed_data.sql`  
**Dependencies:** `001_schema.sql`

**Objects created:**

| Object | Type | Value |
|---|---|---|
| `classes` rows | Data | 4 rows: Class 9, 10, 11, 12 |
| `subjects` rows | Data | 32 rows across all 4 classes |

**Verification (confirmed by live app):** Homepage shows `4 CLASSES` and `32 SUBJECTS`.

---

### 003 — RLS Policies `✅ Likely Applied`

**File:** `supabase/migrations/003_rls_policies.sql`  
**Dependencies:** `001_schema.sql`

**Objects created:**

| Policy | Table | Role | Operation |
|---|---|---|---|
| `classes_public_read` | classes | anon, authenticated | SELECT |
| `classes_admin_all` | classes | authenticated | ALL |
| `subjects_public_read` | subjects | anon, authenticated | SELECT |
| `subjects_admin_all` | subjects | authenticated | ALL |
| `papers_public_read` | papers | anon | SELECT (is_visible=true only) |
| `papers_admin_read` | papers | authenticated | SELECT (all rows) |
| `papers_admin_insert` | papers | authenticated | INSERT |
| `papers_admin_update` | papers | authenticated | UPDATE |
| `papers_admin_delete` | papers | authenticated | DELETE |
| `audit_logs_admin_read` | audit_logs | authenticated | SELECT |
| `audit_logs_admin_insert` | audit_logs | authenticated | INSERT |
| `search_queries_public_insert` | search_queries | anon, authenticated | INSERT |
| `search_queries_admin_read` | search_queries | authenticated | SELECT |

**Total: 13 policies across 5 tables.**

> **Note:** If 003 has NOT been applied, tables are accessible without RLS (no policies = open access). This is a security risk. Run the verification query below to confirm.

---

### 004 — Functions (RPC) `❌ Not Applied`

**File:** `supabase/migrations/004_functions.sql`  
**Dependencies:** `001_schema.sql`, `003_rls_policies.sql`

**Objects to be created:**

| Function | Callable by | Purpose |
|---|---|---|
| `increment_download_count(paper_id_param INTEGER)` | anon, authenticated | Atomically increments `papers.download_count` |
| `get_admin_stats()` | authenticated | Returns 7 aggregate stats in one call |
| `get_search_analytics()` | authenticated | Returns popular + recent search terms as JSONB |
| `get_content_status()` | authenticated | Returns class→subject→exam_type coverage matrix as JSONB |

**GRANT statements in this file:**
```sql
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_admin_stats()                 TO authenticated;
GRANT EXECUTE ON FUNCTION get_search_analytics()            TO authenticated;
GRANT EXECUTE ON FUNCTION get_content_status()              TO authenticated;
```

---

### 005 — Search Analytics `❌ Not Applied`

**File:** `supabase/migrations/005_search_analytics.sql`  
**Dependencies:** `001_schema.sql`, `003_rls_policies.sql`

**Objects to be created:**

| Object | Type | Purpose |
|---|---|---|
| `idx_search_queries_normalised_term` | Index | Speeds up `get_search_analytics()` aggregation |
| `search_term_counts` | View | Top 100 search terms by frequency — admin convenience |
| `prune_old_search_queries(older_than_days INTEGER)` | Function | Deletes search rows older than N days |

**GRANT:**
```sql
GRANT EXECUTE ON FUNCTION prune_old_search_queries(INTEGER) TO authenticated;
```

---

### 006 — Search RPC `❌ Not Applied`

**File:** `supabase/migrations/006_search_rpc.sql`  
**Dependencies:** `001_schema.sql`, `003_rls_policies.sql`

**Objects to be created:**

| Object | Type | Purpose |
|---|---|---|
| `search_papers(q TEXT, p_class_id INTEGER, p_exam_type TEXT, p_paper_type TEXT)` | Function | Cross-table full-text search (papers + subjects + classes) via ILIKE |

**GRANT:**
```sql
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;
```

---

## Verification Queries

Run these in Supabase Dashboard → SQL Editor to confirm current state:

### Tables
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: audit_logs, classes, papers, search_queries, subjects
```

### Functions
```sql
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
-- Expected after 004+005+006: get_admin_stats, get_content_status,
--   get_search_analytics, increment_download_count, prune_old_search_queries, search_papers
```

### RLS policies (003 verification)
```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
-- Expected: 13 policies across 5 tables
```

### Seed data (002 verification)
```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
-- Expected: class_count = 4, subject_count = 32
```

### Views (005 verification)
```sql
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- Expected after 005: search_term_counts
```
