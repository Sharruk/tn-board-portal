# SECURITY_GUIDELINES.md — Security Guidelines
# TN Board Portal

---

## Security Architecture Overview

This project uses a **frontend-only + Supabase** architecture. Security is enforced at the database level via **Row Level Security (RLS)** — not in application code. This is by design.

---

## Core Security Principles

### 1. Never Trust the Client

The browser is untrusted. Any secret that goes to the browser can be extracted.

**What is safe to expose:**
- `VITE_SUPABASE_URL` — just the project URL
- `VITE_SUPABASE_ANON_KEY` — the anonymous/public key, intentionally public

**Why it's safe:** Supabase RLS policies enforce what the anon key can and cannot do. The key alone grants nothing beyond what the policies allow.

**What must NEVER be in the browser:**
- Supabase service_role key — grants full DB bypass
- Admin credentials
- Private API keys of any kind

### 2. RLS Is the Authorization Layer

Every table has RLS enabled. RLS policies control:
- What anonymous users can read
- What authenticated users can read and write
- What no one can access

**Rule:** Never disable RLS on any table. Never create a `SECURITY DEFINER` function that bypasses RLS without explicit need and review.

### 3. Admin Access Is Supabase Auth Only

- Admin login uses Supabase Auth (email/password)
- No admin registration via the app — accounts are created manually via Supabase Dashboard
- Admin session is managed by `AuthContext.jsx`
- `ProtectedRoute` wraps every `/admin/*` route

---

## Environment Variable Security

| Variable | Location | Exposure |
|----------|---------|---------|
| `VITE_SUPABASE_URL` | `frontend/.env.local` (local), Vercel Dashboard (prod) | Public (intentional) |
| `VITE_SUPABASE_ANON_KEY` | `frontend/.env.local` (local), Vercel Dashboard (prod) | Public (intentional) |

**Rules:**
- Never commit `.env.local` or any file with real secrets
- `.env.example` contains only template values, never real keys
- `VITE_` prefix bakes the value into the JS bundle at build time — it is visible to anyone who inspects the bundle

---

## RLS Policy Checklist

For every new table, verify:

- [ ] RLS is enabled: `ALTER TABLE xxx ENABLE ROW LEVEL SECURITY`
- [ ] Anon read policy exists (if public data)
- [ ] Anon write is blocked (unless explicitly needed via RPC)
- [ ] Authenticated read policy exists
- [ ] Authenticated write policy exists (INSERT, UPDATE, DELETE)
- [ ] Grants are explicit: `GRANT EXECUTE ON FUNCTION xxx TO anon, authenticated`

---

## Storage Security

Every Supabase Storage bucket must have:

- **Public SELECT** — `anon` can read (download) files (all three buckets are intentionally public)
- **Authenticated INSERT** — only admin users can upload
- **Authenticated DELETE** — only admin users can delete

Never create a bucket with unauthenticated write access.

---

## Supabase Auth Rules

- Admin users are created manually via Supabase Dashboard (no public signup flow)
- Auth sessions are JWT-based; managed by `AuthContext`
- Logout invalidates the session both client-side and server-side
- Future: MFA support planned for v1.2

---

## Common Security Vulnerabilities to Avoid

### SQL Injection
Not a risk with the Supabase JS client (uses parameterized queries). But in RPC functions, always use parameterized queries, never string concatenation:

```sql
-- ✅ Safe
WHERE papers.title ILIKE '%' || p_query || '%'

-- ❌ Dangerous (never do this)
EXECUTE 'SELECT * FROM papers WHERE title LIKE ''' || p_query || '''';
```

### Exposed Service Role Key
Never use the `service_role` key in the frontend. If you ever need to bypass RLS (e.g., in a scheduled Edge Function), use it only in a Supabase Edge Function — never in the browser bundle.

### Open Admin Routes
Every admin route must be wrapped in `ProtectedRoute`. When adding new admin pages, always verify the route definition in `router/index.jsx` uses `ProtectedRoute`.

### Audit Log Gaps
Every admin action that modifies data must log to `audit_logs`. Verify after implementing any admin feature:
- Upload → logged
- Edit → logged
- Delete → logged
- Bulk upload → logged (per file)

---

## Future Security Improvements

- [ ] Rate limiting on public RPCs (via Supabase Edge Function middleware) — planned v1.3
- [ ] MFA for admin accounts (Supabase Auth TOTP) — planned v1.2
- [ ] Security headers (CSP, X-Frame-Options) via Vercel `headers` config
- [ ] `npm audit` in CI for dependency vulnerability scanning (already in `.github/workflows/`)
