# Vercel Deployment Plan
## TN State Board Learning Platform — React + Supabase on Vercel

---

## Architecture Overview

After migration:

```
GitHub repo (main branch)
        │
        │  git push → auto-deploy
        ▼
    Vercel (free tier)
    ├── Build: cd frontend && npm run build
    ├── Output: frontend/dist/
    ├── SPA routing: vercel.json rewrite
    └── Env vars: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY

        │  All data/auth/storage via HTTPS
        ▼
    Supabase (free tier)
    ├── PostgreSQL (RLS-protected)
    ├── Auth (email/password)
    └── Storage (bucket: papers, public)
```

No server. No backend. No Railway. No Render. Zero infrastructure to maintain.

---

## Prerequisites

1. ✅ Supabase project created with migrations 001–005 applied
2. ✅ `papers` bucket created (Public, 50 MB, PDF only)
3. ✅ Admin user created in Supabase Auth
4. ✅ GitHub repository with the migrated React code
5. ✅ Vercel account (free tier is sufficient)

---

## Step 1 — Supabase Configuration

### Collect these values from Supabase Dashboard → Settings → API

| Value | Where to find it | Used for |
|---|---|---|
| Project URL | Settings → API → Project URL | `VITE_SUPABASE_URL` |
| anon key | Settings → API → anon (public) | `VITE_SUPABASE_ANON_KEY` |

> The `anon` key is safe to embed in the React bundle. RLS policies (applied in migration 003) enforce all access restrictions at the database level. The anon key cannot bypass RLS.

> Do NOT use the `service_role` key in the frontend. It bypasses RLS.

---

## Step 2 — `frontend/vercel.json`

Replace the current placeholder with this final content:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

This single rewrite enables React Router's SPA routing — every path returns `index.html` and React Router handles the navigation. The Supabase API is called directly from the browser, so no backend proxy rewrites are needed.

---

## Step 3 — `frontend/vite.config.js` Cleanup

Remove the proxy configuration (no backend to proxy to):

```javascript
// Before
server: {
  host: '0.0.0.0',
  port: 5000,
  allowedHosts: true,
  strictPort: true,
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
    '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
  },
}

// After
server: {
  host: '0.0.0.0',
  port: 5000,
  allowedHosts: true,
}
```

---

## Step 4 — Deploy to Vercel

### Option A — Vercel Dashboard (recommended for first deploy)

1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repository
3. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add environment variables:
   | Name | Value |
   |---|---|
   | `VITE_SUPABASE_URL` | `https://xxxxxxxxxxxx.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
5. Click **Deploy**

### Option B — Vercel CLI

```bash
cd frontend
npm install -g vercel
vercel env add VITE_SUPABASE_URL
vercel env add VITE_SUPABASE_ANON_KEY
vercel --prod
```

---

## Step 5 — Configure Supabase Allowed Origins

After first Vercel deploy, you'll get a URL like `https://your-app.vercel.app`.

In Supabase Dashboard → **Authentication → URL Configuration**:

| Setting | Value |
|---|---|
| Site URL | `https://your-app.vercel.app` |
| Redirect URLs | `https://your-app.vercel.app/**` |

This ensures Supabase Auth redirects work correctly.

---

## Step 6 — Post-Deployment Verification Checklist

- [ ] `https://your-app.vercel.app/` — Homepage loads with class cards
- [ ] `https://your-app.vercel.app/class/10` — Class 10 subjects load
- [ ] `https://your-app.vercel.app/search?q=maths` — Search returns results
- [ ] Refresh on `/search` — does NOT 404 (SPA routing works)
- [ ] `https://your-app.vercel.app/admin/login` — Login form appears
- [ ] Login with Supabase Auth credentials — dashboard loads
- [ ] Admin dashboard stats load (4 classes, 32 subjects shown)
- [ ] PDF upload works → file appears in Supabase Storage
- [ ] PDF download increments `download_count`
- [ ] Delete paper removes from Storage and DB

---

## Automatic Deployments

After connecting GitHub:
- Every `git push` to `main` → Vercel auto-rebuilds and deploys
- Pull request branches → Vercel creates preview URLs automatically
- Zero-downtime deployments

---

## Cost Estimate (Free Tiers)

| Service | Free Tier Limit | Expected Usage |
|---|---|---|
| Vercel | 100 GB bandwidth/month, unlimited deploys | Well within limits |
| Supabase DB | 500 MB | Years at student portal volume |
| Supabase Storage | 1 GB | ~20,000 PDFs at 50 KB avg |
| Supabase Bandwidth | 5 GB/month | Sufficient for thousands of downloads |
| Supabase Auth | Unlimited users | Only 1 admin user needed |

**Estimated monthly cost: $0** on both free tiers.

---

## Custom Domain (Optional)

In Vercel Dashboard → Project → Settings → Domains:
1. Add your domain (e.g., `tnboard.example.com`)
2. Update DNS records at your registrar as instructed
3. Update Supabase → Authentication → URL Configuration with the custom domain
4. Vercel provides HTTPS automatically via Let's Encrypt

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase public anon key (safe for frontend) |

**That's it. Two environment variables.** Compared to 7+ variables in the FastAPI setup.
