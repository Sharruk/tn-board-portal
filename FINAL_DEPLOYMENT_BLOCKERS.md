# FINAL DEPLOYMENT BLOCKERS
TN State Board Learning Platform — End-to-End Verification Report
Date: 2026-06-21

---

## VERDICT

**2 BLOCKERS REMAIN — must fix before deploying**

Both are Supabase configuration steps (no code changes needed).
After fixing them, the project is ready for Vercel deployment.

---

## LIVE API VERIFICATION (all passed via curl)

| Check | Result |
|---|---|
| `GET /rest/v1/classes` (anon key) | ✅ 4 rows returned |
| `GET /rest/v1/subjects` (anon key) | ✅ 32 rows returned |
| `GET /rest/v1/papers?is_visible=eq.true` (anon key) | ✅ 200 OK (0 rows — no papers uploaded yet) |
| `POST /rest/v1/rpc/search_papers` (anon key) | ✅ 200 OK (RPC reachable) |
| `POST /rest/v1/rpc/get_admin_stats` (anon key) | ✅ Returns stats (4 classes, 32 subjects, 0 papers) |
| Storage bucket object list (anon key) | ✅ Reachable — returns [] (empty, no files yet) |

---

## PAGE VERIFICATION (all passed via live screenshot)

| Page | Route | Status |
|---|---|---|
| Homepage hero + search | `/` | ✅ Renders, no console errors |
| Class page (real data) | `/class/9` | ✅ 5 subjects from Supabase |
| Class page (real data) | `/class/10` | ✅ 5 subjects from Supabase |
| Search page | `/search` | ✅ Renders, filters visible |
| Admin login | `/admin/login` | ✅ Renders, uses supabase.auth.signInWithPassword |
| React Router | All routes | ✅ No routing errors |

---

## DEPENDENCY AUDIT (all passed)

| Check | Result |
|---|---|
| `localhost:8000` references in `frontend/src/` | ✅ NONE |
| `/api/v1` references in `frontend/src/` | ✅ NONE |
| `axios` imports in `frontend/src/` | ✅ NONE |
| `axios` in `package.json` | ✅ REMOVED |
| JWT / localStorage token auth | ✅ NONE (replaced by Supabase Auth) |
| Vite proxy to FastAPI backend | ✅ REMOVED from vite.config.js |
| Admin auth method | ✅ `supabase.auth.signInWithPassword` |
| Admin session method | ✅ `supabase.auth.getSession` + `onAuthStateChange` |

---

## BUILD VERIFICATION

```
npm run build
✓ 105 modules transformed.
dist/index.html                   0.57 kB  │ gzip:   0.36 kB
dist/assets/index-BsDm6xq4.css   35.40 kB │ gzip:   6.39 kB
dist/assets/index-ByMVbSgH.js   529.94 kB │ gzip: 146.88 kB
✓ built in 3.92s
```

**Result: BUILD SUCCESSFUL — zero errors.**

Note: chunk size warning (529 kB) is cosmetic only, does not block deployment.
Can be resolved post-launch with dynamic imports if needed.

---

## BLOCKER 1 — Storage Upload Policies Not Set

**Severity: CRITICAL — paper uploads will fail for admin**

**What fails:** When the admin uploads a PDF via the admin panel,
`supabase.storage.from('papers').upload(...)` will return 403 Forbidden
because the `papers` storage bucket has no INSERT or DELETE policies.

Public buckets allow public *reads* automatically, but *writes* still
require explicit storage policies.

**Fix — run this SQL in Supabase SQL Editor:**

```sql
-- Allow authenticated admins to upload PDFs to the papers bucket
CREATE POLICY "Admin can upload papers"
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (bucket_id = 'papers');

-- Allow authenticated admins to delete papers from storage
CREATE POLICY "Admin can delete papers"
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (bucket_id = 'papers');

-- Allow public read (explicit, in case the auto-policy is missing)
CREATE POLICY "Public can read papers"
  ON storage.objects
  FOR SELECT
  TO anon
  USING (bucket_id = 'papers');
```

**Alternatively** — do this in the Supabase dashboard:
Storage → papers bucket → Policies → New policy (use the template "Give users access to a folder only to authenticated users", adapt for INSERT/DELETE on bucket_id = 'papers')

---

## BLOCKER 2 — Admin Email Confirmation (may block login)

**Severity: HIGH — admin cannot log in if email is unconfirmed**

**What fails:** By default, Supabase Auth requires email confirmation
before `signInWithPassword` succeeds. If the admin user created in Step 3
has not confirmed their email, login returns:
`"Email not confirmed"`

**Fix (choose one):**

**Option A — Disable email confirmation (recommended for this project):**
1. Supabase → Authentication → Providers → Email
2. Toggle OFF "Enable email confirmations"
3. Save

**Option B — Confirm the admin user manually:**
1. Supabase → Authentication → Users
2. Find your admin user
3. Click the three-dot menu → "Send confirmation email" OR
   click the user row → mark as confirmed

---

## CLEAN STATE SUMMARY

| Item | State |
|---|---|
| React + Vite + Tailwind frontend | ✅ Active |
| Supabase PostgreSQL | ✅ Connected (4 tables, 36 rows seeded) |
| Supabase Auth | ✅ Connected (admin user exists) |
| Supabase Storage (`papers` bucket) | ✅ Exists, public read working |
| FastAPI backend | ⚫ Inactive (code in `/backend/` — not used by frontend) |
| Old Flask files (`app.py`, etc.) | ⚫ Inactive at repo root — not used by frontend |
| `axios` package | ✅ Removed |
| Vite proxy config | ✅ Removed (no localhost:8000 proxy) |

---

## AFTER FIXING THE 2 BLOCKERS

**PROJECT READY FOR VERCEL DEPLOYMENT**

### Vercel Settings

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

### Required Environment Variables (set in Vercel dashboard)

| Variable | Value |
|---|---|
| `VITE_SUPABASE_URL` | `https://fcxvrsgcvmlowehpilvr.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | *(your anon key — copy from Supabase → Settings → API)* |

### Vercel Rewrite Rule (for React Router SPA)

Add this to `frontend/vercel.json`:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```
Without this, direct URL navigation to `/class/9` or `/admin/login` will 404 on Vercel.

---

## ACTION CHECKLIST

- [ ] **BLOCKER 1**: Run storage policy SQL in Supabase SQL Editor
- [ ] **BLOCKER 2**: Disable email confirmation OR confirm admin user
- [ ] Create `frontend/vercel.json` with SPA rewrite rule
- [ ] Deploy to Vercel with root directory = `frontend`
- [ ] Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in Vercel env vars
