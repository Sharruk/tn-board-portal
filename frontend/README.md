# TN Board Portal — Frontend Application

Modern single-page application built with React 18, Vite, and Tailwind CSS for Tamil Nadu State Board students, educators, and administrators.

---

## 1. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Runtime / Library** | React | 18.3.1 | Core UI framework |
| **Bundler / Dev Server** | Vite | 5.4.x | Fast build tool & reverse proxy server |
| **Styling** | Tailwind CSS + PostCSS | 3.4.x | Utility-first responsive design |
| **Routing** | React Router DOM | 6.27.x | Declarative client-side routing & guards |
| **Authentication** | Firebase Web SDK | 12.18.x | Google Sign-In with OAuth 2.0 |
| **Database & Storage Client** | Supabase JS | 2.108.x | Public CDN downloads & public queries |
| **API Client** | Native Fetch (`lib/api.js`) | — | Centralized FastAPI client |

---

## 2. Local Development

### Option A: Full-Stack Docker Compose (Recommended)
From the repository root, start both the frontend and backend together:
```bash
docker compose up --build -d
```
- **Frontend URL**: [http://localhost:5000](http://localhost:5000)
- Source code edits in `src/` and static assets in `public/` are mounted into the container and update immediately via Vite polling.

### Option B: Standalone Local Vite
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Create local environment file
cp .env.example .env.local
# Edit .env.local with your Firebase and Supabase credentials

# 4. Start Vite development server
npm run dev
```

---

## 3. Reverse Proxy & API Routing

In development (both inside Docker and locally), the browser interacts exclusively with the frontend origin:
- All `/api/*`, `/health`, and `/docs` HTTP requests made by the frontend application are routed through Vite's built-in reverse proxy in `vite.config.js`.
- Inside Docker, Vite proxies requests to `http://backend:8000` via the internal Docker bridge network (`VITE_API_PROXY_TARGET=http://backend:8000`).
- This guarantees the browser never attempts to connect directly to internal Docker service names, completely avoiding CORS and DNS resolution issues on the host.

In production (Vercel):
- Frontend and backend share the same origin (`https://tn-board-portal.vercel.app`).
- `apiFetch()` in `src/lib/api.js` uses relative paths (`/api/v1/...`), ensuring zero CORS preflight overhead and seamless serverless routing.

---

## 4. Production Build

To verify the production build locally:
```bash
npm run build
```
Build artifacts are placed in `frontend/dist/` and served in production by Vercel's Edge Network.