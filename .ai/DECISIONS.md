# DECISIONS.md — Architectural Decisions Log
# TN Board Portal

> Every significant architectural decision is recorded here with rationale.
> Before making a similar decision, read this file to understand past reasoning.

---

## Format

Each decision follows this template:

```
### [ADR-NNN] Title
Date: YYYY-MM-DD
Status: Accepted | Superseded by ADR-NNN | Deprecated
Context: Why was this decision needed?
Decision: What was decided?
Rationale: Why was this the right choice?
Consequences: What are the tradeoffs or implications?
```

---

### [ADR-001] Frontend-Only Architecture (No Custom Backend)

**Date:** Pre-v1.0 (before 2026-07-01)
**Status:** Accepted

**Context:**
The project needed a database, auth system, and file storage. The question was whether to build a custom Node.js/Express backend or use a BaaS.

**Decision:**
Use Supabase as the sole backend. No custom server. The React SPA communicates directly with Supabase via the JS client.

**Rationale:**
- Supabase provides managed Postgres, Auth, Storage, and CDN out of the box
- Zero backend infrastructure to maintain or secure
- RLS policies enforce authorization at the DB level — more reliable than application-level auth
- Faster development velocity
- Demonstrates ability to design secure, serverless architectures

**Consequences:**
- Cannot run arbitrary server-side code (use Supabase Edge Functions or Vercel serverless functions if needed)
- Complex business logic must live in PostgreSQL RPC functions
- No custom rate limiting without an Edge Function layer

---

### [ADR-002] Supabase RPC Functions for Cross-Table Operations

**Date:** Pre-v1.0
**Status:** Accepted

**Context:**
PostgREST (Supabase's REST layer) cannot efficiently filter across JOINs. Full-site search needs to query papers, notices, and news simultaneously with different filter criteria.

**Decision:**
Use PostgreSQL `SECURITY DEFINER` RPC functions for:
- Full-site search (`search_papers`, `search_notices`, `search_news`)
- Admin statistics (`get_admin_stats`, `get_content_status`)
- Atomic counters (`increment_download_count`, `record_notice_view`, `record_notice_download`, `increment_news_views`)

**Rationale:**
- RPC functions have full SQL expressiveness
- Atomic counter increments prevent race conditions
- SECURITY DEFINER allows anon users to call counters without bypassing RLS on other operations
- Complex JOINs and aggregations are more efficient in Postgres than in JS

**Consequences:**
- New cross-table features require new migrations (not just service layer changes)
- Debugging requires access to Supabase SQL logs
- All functions must be explicitly GRANTed to anon/authenticated

---

### [ADR-003] Sequential Numbered Migrations (No Supabase CLI)

**Date:** Pre-v1.0
**Status:** Accepted (to be upgraded in v1.1)

**Context:**
The project needed a way to evolve the database schema in a trackable, repeatable way. Two options: Supabase CLI (`supabase db push`) or manual sequential SQL files.

**Decision:**
Use manually managed sequential SQL files (`001_schema.sql`, `002_seed_data.sql`, ...) applied via Supabase Dashboard SQL Editor.

**Rationale:**
- Simple to understand and use
- No CLI tool dependency
- Each file is self-contained and human-readable
- Easy to apply on any Supabase project (no local Supabase CLI setup required)

**Consequences:**
- Manual process — easy to forget a migration or apply out of order
- No automatic state tracking (unlike `supabase db push`)
- Planned upgrade to Supabase CLI in v1.1

---

### [ADR-004] Tailwind CSS (Utility-First, No Component Library)

**Date:** Pre-v1.0
**Status:** Accepted

**Context:**
Styling approach. Options: plain CSS, Tailwind CSS, CSS modules, a component library (MUI, Chakra, shadcn/ui).

**Decision:**
Use Tailwind CSS with no component library.

**Rationale:**
- Full control over design without fighting a component library's defaults
- Tailwind's utility classes are already in the project — consistent approach
- PostCSS/Autoprefixer pipeline is already configured in Vite
- No extra JavaScript runtime overhead (unlike MUI, Chakra)
- Demonstrates CSS skill rather than hiding it behind a library

**Consequences:**
- More verbose JSX (Tailwind classes inline)
- No pre-built accessible components (must handle a11y manually)
- Dark mode requires coordinated `dark:` class usage across all components

---

### [ADR-005] React Context (No Redux or Zustand)

**Date:** Pre-v1.0
**Status:** Accepted

**Context:**
Global state management. Options: React Context, Redux, Zustand, Jotai, etc.

**Decision:**
Use only React Context (`AuthContext`) for global state. No external state management library.

**Rationale:**
- Only one piece of truly global state exists: the Supabase Auth session
- Prop passing is sufficient for component communication at this scale
- Adding Redux/Zustand would add complexity and bundle size without benefit
- Context is sufficient until the app scales to dozens of interconnected global state slices

**Consequences:**
- If global state needs grow significantly (v2.0+), a state management library may need to be added
- `useContext(AuthContext)` must be available in all admin components

---

### [ADR-006] Three Separate Supabase Storage Buckets

**Date:** Migration 008 / 011 (v1.0)
**Status:** Accepted

**Context:**
Where to store uploaded files. Options: one bucket for everything, or separate buckets by content type.

**Decision:**
Three separate public buckets:
- `papers` — Question paper and answer key PDFs
- `official-updates` — Notice attachments (any file type)
- `news-media` — News thumbnail images

**Rationale:**
- Different content types have different access patterns and file type requirements
- Separate buckets allow different size limits and MIME type restrictions per bucket
- Easier to add per-bucket policies in the future
- Cleaner URL structure

**Consequences:**
- Services must know which bucket to use for each content type
- Adding a new content type requires a new migration to configure the bucket

---

### [ADR-007] ILIKE Search (vs. Full-Text Search)

**Date:** Migration 006 (v1.0)
**Status:** Accepted → To be superseded by ADR-008

**Context:**
Search implementation. Options: ILIKE pattern matching, PostgreSQL `tsvector`/`tsquery` full-text search, Algolia, etc.

**Decision (v1.0):**
Use ILIKE (`LIKE '%term%'`) in RPC functions for search across papers, notices, and news.

**Rationale:**
- Simpler to implement in the initial version
- Sufficient for the current data volume (hundreds of papers, not millions)
- No additional infrastructure or cost

**Consequences:**
- No relevance ranking (all results are equal)
- No typo tolerance
- Slower on very large datasets (no GIN index benefit)
- Known issue documented in CHANGELOG.md v1.0

**Planned upgrade in ADR-008 (v1.1):**
Replace ILIKE with `tsvector`/`tsquery` and GIN indexes.

---

### [ADR-008] tsvector/tsquery Full-Text Search (Planned)

**Date:** Planned for v1.1 (Q3 2026)
**Status:** Planned — supersedes ADR-007

**Context:**
See ADR-007. ILIKE has known limitations. v1.1 plans to upgrade search quality.

**Planned Decision:**
Add `tsvector` columns and GIN indexes to papers, notices, and news tables. Rewrite search RPCs to use `tsquery` with `ts_rank()` for relevance ranking.

**Rationale:**
- Better search quality with relevance ranking
- Faster performance at scale (GIN index)
- Supports phrase queries and boolean operators
- Demonstrates PostgreSQL full-text search expertise

**Migration:** `015_xxx.sql` (next in sequence)
