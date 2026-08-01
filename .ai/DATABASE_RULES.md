# DATABASE_RULES.md — Database Rules & Migration Guide
# TN Board Portal

> The database is in production. Real data lives here. These rules are non-negotiable.

---

## The Golden Rule

**Never edit a migration that has already been applied to production.**

All database changes must be **additive new migrations**, never edits to existing ones.

---

## Migration Numbering

Migrations are sequentially numbered:

```
001_schema.sql              ← Classes, subjects, papers, audit_logs, search_queries
002_seed_data.sql           ← Classes 9–12 seed rows, subjects
003_rls_policies.sql        ← Row Level Security for papers, classes, subjects
004_functions.sql           ← get_admin_stats, increment_download_count
005_search_analytics.sql    ← search_queries table and analytics
006_search_rpc.sql          ← search_papers() ILIKE RPC
007_paper_status.sql        ← status column (draft|published|archived)
008_official_notices.sql    ← official_notices table, RPCs, storage
009_fix_notices_grants.sql  ← Permission grants for notices RPCs
010_add_youtube_url.sql     ← youtube_url on official_notices
011_news_updates.sql        ← news_updates table, RPCs, storage
012_fix_news_grants.sql     ← Permission grants for news RPCs
013_preserve_original_filenames.sql  ← original_filename column
014_update_search_papers_rpc.sql    ← Updated search_papers RPC

NEXT: 015_xxx.sql
```

**Next migration must be numbered 015.**

---

## Migration File Template

Every new migration MUST follow this structure:

```sql
-- Migration: 015_your_feature_name.sql
-- Purpose: [One sentence description]
-- Backward compatible: YES / NO (explain if NO)
-- Affects tables: [list]
-- Affects RLS: YES/NO
-- Affects RPCs: YES/NO
-- Created: YYYY-MM-DD

-- ============================================
-- 1. Schema changes
-- ============================================

ALTER TABLE papers ADD COLUMN IF NOT EXISTS year_filter INTEGER;

-- ============================================
-- 2. RLS policy updates (if needed)
-- ============================================

-- Drop and recreate affected policies only if needed
-- Never delete existing policies without a replacement

-- ============================================
-- 3. RPC updates (if needed)
-- ============================================

CREATE OR REPLACE FUNCTION search_papers(...) ...

-- ============================================
-- 4. Grants (always explicit)
-- ============================================

GRANT EXECUTE ON FUNCTION search_papers TO anon, authenticated;

-- ============================================
-- 5. Indexes (if needed)
-- ============================================

CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
```

---

## Database Schema

### Tables

#### `classes`
```sql
id          INTEGER PRIMARY KEY
name        TEXT NOT NULL         -- "Class 9", "Class 10", etc.
slug        TEXT UNIQUE           -- "class-9"
created_at  TIMESTAMPTZ DEFAULT NOW()
```

#### `subjects`
```sql
id          SERIAL PRIMARY KEY
class_id    INTEGER REFERENCES classes(id)
name        TEXT NOT NULL
slug        TEXT
created_at  TIMESTAMPTZ DEFAULT NOW()
```

#### `papers`
```sql
id                  SERIAL PRIMARY KEY
subject_id          INTEGER REFERENCES subjects(id)
title               TEXT NOT NULL
exam_type           TEXT              -- 'quarterly', 'half-yearly', 'annual', 'public'
paper_type          TEXT              -- 'question-paper', 'answer-key'
year                INTEGER
file_path           TEXT              -- path in Supabase Storage
public_url          TEXT              -- full CDN URL
original_filename   TEXT              -- preserved original upload filename
youtube_url         TEXT              -- optional YT embed
status              TEXT DEFAULT 'draft'   -- 'draft' | 'published' | 'archived'
download_count      INTEGER DEFAULT 0
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()
```

#### `official_notices`
```sql
id              SERIAL PRIMARY KEY
title           TEXT NOT NULL
category        TEXT              -- 'circular', 'timetable', 'result', 'order', 'other'
description     TEXT
file_path       TEXT
public_url      TEXT
original_filename TEXT
youtube_url     TEXT
class_id        INTEGER REFERENCES classes(id)  -- nullable
is_pinned       BOOLEAN DEFAULT false
is_visible      BOOLEAN DEFAULT true
expires_at      TIMESTAMPTZ                      -- nullable
view_count      INTEGER DEFAULT 0
download_count  INTEGER DEFAULT 0
created_at      TIMESTAMPTZ DEFAULT NOW()
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

#### `news_updates`
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
title           TEXT NOT NULL
slug            TEXT UNIQUE NOT NULL
summary         TEXT
content         TEXT
category        TEXT              -- 'exam', 'result', 'circular', 'update', 'other'
tags            TEXT[]
status          TEXT DEFAULT 'draft'   -- 'draft' | 'published'
thumbnail_url   TEXT
youtube_url     TEXT
view_count      INTEGER DEFAULT 0
published_at    TIMESTAMPTZ
created_at      TIMESTAMPTZ DEFAULT NOW()
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

#### `audit_logs`
```sql
id          SERIAL PRIMARY KEY
admin_id    UUID REFERENCES auth.users(id)
action      TEXT NOT NULL     -- 'upload', 'bulk_upload', 'edit', 'delete', 'login', 'logout'
entity_type TEXT              -- 'paper', 'notice', 'news'
entity_id   TEXT
details     JSONB
ip_address  TEXT
created_at  TIMESTAMPTZ DEFAULT NOW()
```

#### `search_queries`
```sql
id              SERIAL PRIMARY KEY
query_term      TEXT NOT NULL
result_count    INTEGER
created_at      TIMESTAMPTZ DEFAULT NOW()
```

---

## PostgreSQL RPC Functions

| Function | Purpose | Access |
|----------|---------|--------|
| `search_papers(q, p_class_id, p_exam_type, p_paper_type)` | ILIKE search across papers | anon, authenticated |
| `search_notices(q, p_category, p_class_id, p_year)` | ILIKE search across notices | anon, authenticated |
| `search_news(q, p_category, p_limit)` | ILIKE search across news | anon, authenticated |
| `get_admin_stats()` | Aggregate dashboard stats | authenticated |
| `get_content_status()` | Per-subject published vs draft counts | authenticated |
| `increment_download_count(paper_id)` | Atomic download counter | anon, authenticated |
| `record_notice_view(id)` | Atomic notice view counter | anon, authenticated |
| `record_notice_download(id)` | Atomic notice download counter | anon, authenticated |
| `increment_news_views(id)` | Atomic news view counter | anon, authenticated |

---

## Supabase Storage Buckets

| Bucket | Public | Used For |
|--------|--------|---------|
| `papers` | ✅ | Question paper and answer key PDFs |
| `official-updates` | ✅ | Notice attachments (PDF, images, Office docs) |
| `news-media` | ✅ | News article thumbnails (JPEG, PNG, WebP, GIF) |

All buckets:
- Public SELECT: `anon` can read (download) files
- Authenticated INSERT/DELETE: only admin users

---

## RLS Rules Summary

| Table | anon | authenticated |
|-------|------|---------------|
| `classes` | SELECT | SELECT |
| `subjects` | SELECT | SELECT |
| `papers` | SELECT (status='published') | ALL |
| `official_notices` | SELECT (visible, not expired) | ALL |
| `news_updates` | SELECT (published, published_at ≤ NOW()) | ALL |
| `audit_logs` | None | SELECT (own) |
| `search_queries` | INSERT (via RPC) | ALL |

---

## Do Not Principles (Database)

- Never `DROP TABLE` in a migration
- Never `DROP COLUMN` without confirming it is unused in ALL service files
- Never remove an RPC function without verifying no service calls it
- Never change a column type that contains production data without a safe migration path
- Never remove RLS policies without a direct replacement
- Never use `TRUNCATE` in a migration
- Always use `IF NOT EXISTS` / `IF EXISTS` in migrations for idempotency
- Always use `CREATE OR REPLACE FUNCTION` for RPC updates
- Always explicitly GRANT after creating a new function

---

## Applying Migrations

Migrations are applied manually via Supabase SQL Editor:

1. Go to: Supabase Dashboard → SQL Editor → New Query
2. Paste the migration file contents
3. Execute
4. Verify in Table Editor

**Future:** Migrate to `supabase db push` with Supabase CLI (planned in v1.1).
