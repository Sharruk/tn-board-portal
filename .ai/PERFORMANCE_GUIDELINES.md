# PERFORMANCE_GUIDELINES.md — Performance Guidelines
# TN Board Portal

---

## Performance Philosophy

This is a static SPA hosted on Vercel's global CDN, backed by Supabase. Performance should be excellent by default. The goal is to never degrade it.

---

## Current Performance Characteristics

| Metric | Current Status |
|--------|---------------|
| Hosting | Vercel CDN — near-zero latency for static assets |
| Database | Supabase managed Postgres — queries should be <100ms |
| Storage | Supabase CDN — PDF downloads served from CDN |
| Bundle | Vite build with tree-shaking and ES module splitting |
| Search debounce | 400ms delay before firing RPC |

---

## Frontend Performance Rules

### Bundle Size

- Do NOT add large dependencies without justification (charts, animation libraries, etc.)
- Before adding any npm package, check its bundle size on [bundlephobia.com](https://bundlephobia.com)
- The current dependency list is intentionally minimal:
  - `react`, `react-dom` — essential
  - `react-router-dom` — essential
  - `@supabase/supabase-js` — essential
  - Tailwind CSS — dev-only, zero runtime cost

### Code Splitting (Planned v1.1)

Lazy-load heavy page components:

```jsx
import { lazy, Suspense } from 'react';

const SearchPage = lazy(() => import('./pages/SearchPage'));
const AdminDashboard = lazy(() => import('./pages/admin/DashboardPage'));

// Wrap in Suspense with a fallback
<Suspense fallback={<LoadingSpinner />}>
  <SearchPage />
</Suspense>
```

### Image Optimization (Planned v1.1)

- Use `loading="lazy"` on all `<img>` tags
- Use WebP format where possible (news thumbnails)
- Avoid large images in the bundle

---

## Database Performance Rules

### Always Filter Before Fetching

```js
// ✅ Good — filter at DB level
.from('papers')
.select('id, title, year, exam_type')  // only needed columns
.eq('subject_id', subjectId)
.eq('status', 'published')
.order('year', { ascending: false })
.limit(50)

// ❌ Bad — fetch everything, filter in JS
.from('papers')
.select('*')
```

### Use Indexes

New columns used in WHERE clauses need indexes. Add them in the migration:

```sql
CREATE INDEX IF NOT EXISTS idx_papers_subject_status ON papers(subject_id, status);
CREATE INDEX IF NOT EXISTS idx_news_status_published ON news_updates(status, published_at);
```

### Atomic Counter RPCs

Download counts use `increment_download_count()` RPC — an atomic PostgreSQL operation. This is intentional and correct. Never update counters with a `SELECT` + `UPDATE` pattern from the client.

### Search Performance

Current: ILIKE search (acceptable for current data volume)
Planned v1.1: `tsvector`/`tsquery` with GIN index for ranked full-text search

```sql
-- Planned: Add tsvector index
ALTER TABLE papers ADD COLUMN search_vector tsvector;
CREATE INDEX idx_papers_search ON papers USING gin(search_vector);
```

### Avoid N+1 Queries

Never fetch a list of items and then fetch details for each item in a loop:

```js
// ❌ N+1 — one query per paper
for (const paper of papers) {
  const subject = await getSubject(paper.subject_id);
}

// ✅ Join at DB level
.from('papers')
.select('*, subjects(name, slug)')
.eq('status', 'published')
```

---

## Supabase Performance Rules

- Use `.select('col1, col2')` — never `.select('*')` in production (fetch only needed columns)
- Use `.limit(n)` on list queries — never unbounded fetches
- Use Postgres views or RPC functions for complex aggregations (don't do them in JS)
- `Promise.all()` for parallel independent queries (already used in search)

---

## Search Performance

The search uses a 400ms debounce before firing RPCs. This is intentional.

```jsx
// Current implementation in SearchPage
useEffect(() => {
  const timer = setTimeout(() => {
    if (query.trim()) performSearch();
  }, 400);
  return () => clearTimeout(timer);
}, [query]);
```

Do not reduce the debounce below 300ms without measuring the impact on Supabase RPC usage.

---

## Vercel Performance

The `vercel.json` catch-all rewrite is the only routing config. It serves `index.html` for all routes — this is required for React Router to work and does not impact performance.

Vercel automatically:
- Serves JS/CSS from CDN edge nodes globally
- Applies gzip/brotli compression
- Sets long cache headers for hashed assets

Do not add custom caching headers without understanding Vercel's default caching behavior.

---

## Performance Monitoring (Future)

- Planned v2.0: Analytics dashboard using Recharts for download and search trends
- Core Web Vitals monitoring via Vercel Analytics (can be enabled without code changes)
