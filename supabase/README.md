# Supabase Setup Guide
## TN State Board Learning Platform

This directory contains all Supabase migration SQL files. Run them in order against a fresh Supabase project to set up the complete backend.

---

## Prerequisites

- A Supabase account (free at [supabase.com](https://supabase.com))
- A new Supabase project created for this app
- Access to the Supabase Dashboard SQL Editor

---

## Step 1 — Apply Migrations

Open the **SQL Editor** in your Supabase Dashboard (left sidebar → SQL Editor → New query).

Run each file **in order**, one at a time. Paste the contents, click **Run**, and confirm no errors before moving to the next.

| Order | File | What it does |
|-------|------|-------------|
| 1 | `migrations/001_schema.sql` | Creates all 5 tables with constraints and indexes |
| 2 | `migrations/002_seed_data.sql` | Seeds 4 classes and 32 subjects |
| 3 | `migrations/003_rls_policies.sql` | Enables Row Level Security on all tables |
| 4 | `migrations/004_functions.sql` | Creates RPC functions for download tracking, stats, analytics |
| 5 | `migrations/005_search_analytics.sql` | Adds analytics view and retention cleanup function |

### Verify after migration 002

Run this query to confirm the seed data is correct:

```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,   -- must be 4
  (SELECT COUNT(*) FROM subjects) AS subject_count;  -- must be 32
```

### Verify after migration 003

Run this query to confirm all RLS policies are active:

```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
```

Expected: **12 policies** across 5 tables.

---

## Step 2 — Create the Admin User

Supabase Auth manages the admin login. There is no longer a local `admins` table.

1. Go to **Authentication** in the left sidebar.
2. Click **Users** → **Add user** → **Create new user**.
3. Enter:
   - **Email:** your admin email (e.g. `admin@yourdomain.com`)
   - **Password:** minimum 12 characters — use letters, numbers, and symbols
   - Check **"Auto-confirm user"** (otherwise you must click a verification link)
4. Click **Create User**.
5. Copy the user's **UID** (UUID) — you may need it for troubleshooting.

> Do NOT use `admin@tnboard.local` or `admin123` in production.

---

## Step 3 — Create the Storage Bucket

1. Go to **Storage** in the left sidebar.
2. Click **New bucket**.
3. Configure:
   - **Name:** `papers`
   - **Public bucket:** ON (students need public URLs to view/download PDFs)
   - **File size limit:** `52428800` (50 MB — matches `MAX_FILE_SIZE_MB` in the backend)
   - **Allowed MIME types:** `application/pdf`
4. Click **Create bucket**.

### Storage RLS policy (add after creating the bucket)

The bucket must allow authenticated admins to upload and delete, and allow public download.

In **Storage → Policies**, add these policies for the `papers` bucket:

**Allow public downloads (SELECT):**
```sql
CREATE POLICY "papers_bucket_public_read"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'papers');
```

**Allow admin uploads (INSERT):**
```sql
CREATE POLICY "papers_bucket_admin_insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

**Allow admin deletions (DELETE):**
```sql
CREATE POLICY "papers_bucket_admin_delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

---

## Step 4 — Collect Your API Keys

Go to **Settings → API** in the Supabase Dashboard.

| Key | Where to use | How to get |
|-----|-------------|-----------|
| **Project URL** | `VITE_SUPABASE_URL` in Vercel / `.env.local` | Settings → API → Project URL |
| **anon** key | `VITE_SUPABASE_ANON_KEY` in Vercel / `.env.local` | Settings → API → Project API keys → `anon` |
| **service_role** key | Never in frontend — admin scripts only | Settings → API → Project API keys → `service_role` |

> The `anon` key is safe to embed in the React bundle. Row Level Security (set up in migration 003) enforces all access restrictions — the anon key alone cannot bypass RLS.

---

## Functions Reference

These database functions are callable from the React frontend via `supabase.rpc()`:

| Function | Callable by | Purpose |
|----------|-------------|---------|
| `increment_download_count(paper_id_param)` | anon, authenticated | Atomically increments `papers.download_count` |
| `get_admin_stats()` | authenticated | Returns all dashboard stats in one call |
| `get_search_analytics()` | authenticated | Returns popular and recent searches |
| `get_content_status()` | authenticated | Returns class/subject/exam coverage matrix |
| `prune_old_search_queries(days)` | authenticated | Deletes search rows older than N days |

---

## Free Tier Limits

| Resource | Supabase Free Tier | Expected Usage |
|----------|-------------------|---------------|
| Database | 500 MB | Years at typical student portal volume |
| Storage | 1 GB | ~20,000 PDFs at 50 KB average |
| Bandwidth | 5 GB / month | Sufficient for thousands of downloads |
| Max file size | 50 MB (configured) | Standard exam PDFs are 1–5 MB |
| Auth users | Unlimited | Only 1 admin user needed |

---

## Maintenance

### Prune old search data (optional)

Run this in the SQL Editor if the `search_queries` table grows large:

```sql
SELECT prune_old_search_queries(90);  -- delete entries older than 90 days
```

### Reset admin password

In Supabase Dashboard → Authentication → Users → find your admin user → **Send password reset**.

Or set a new password directly:
```sql
-- In SQL Editor (replaces the password without email verification)
UPDATE auth.users
SET    encrypted_password = crypt('YOUR_NEW_PASSWORD', gen_salt('bf'))
WHERE  email = 'admin@yourdomain.com';
```

### Check RLS is working

Test from the Supabase API explorer (unauthenticated):
- `SELECT * FROM papers WHERE is_visible = false` → should return 0 rows (RLS hides them)
- `SELECT * FROM audit_logs` → should return 0 rows (anon blocked)
- `SELECT * FROM search_queries` → should return 0 rows (anon blocked)
