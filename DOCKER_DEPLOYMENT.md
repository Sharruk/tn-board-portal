# Docker Deployment — TN State Board Learning Platform

---

## Prerequisites

- Docker 24+ — https://docs.docker.com/get-docker/
- Docker Compose v2+ — bundled with Docker Desktop

---

## Files

| File                  | Purpose                                          |
|-----------------------|--------------------------------------------------|
| `backend/Dockerfile`  | Builds the FastAPI backend image                 |
| `docker-compose.yml`  | Orchestrates PostgreSQL + backend + frontend     |
| `.dockerignore`       | Excludes unnecessary files from the build context|

---

## Local Development with Docker Compose

### 1 — Configure environment
```bash
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY at minimum
# DATABASE_URL is handled by docker-compose (see below)
```

### 2 — Start the full stack
```bash
docker compose up --build
```

This starts three services:
- **db** — PostgreSQL 16 on port 5432
- **backend** — FastAPI on port 8000
- **frontend** — Vite dev server on port 5000

### 3 — Seed the database (first run only)
```bash
docker compose exec backend python seed.py
```

### 4 — Change the admin password
```bash
docker compose exec backend python /app/../change_admin_password.py
```

### 5 — Open the app
- Public portal: http://localhost:5000
- API docs: http://localhost:8000/docs
- Admin login: http://localhost:5000/admin/login

### Run in background (detached)
```bash
docker compose up --build -d
```

### View logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Stop and clean up
```bash
# Stop services (keep volumes)
docker compose down

# Stop and remove volumes (wipes the database)
docker compose down -v
```

---

## Building the Backend Image Alone

```bash
cd backend
docker build -t tnboard-backend:latest .
```

### Run the backend container
```bash
docker run \
  -e DATABASE_URL="postgresql://user:pass@host:5432/tnboard" \
  -e JWT_SECRET_KEY="your-secret-key" \
  -e CORS_ORIGINS="http://localhost:5000" \
  -e STORAGE_BACKEND="local" \
  -p 8000:8000 \
  tnboard-backend:latest
```

---

## Production Docker Build

For production, build the React frontend and let FastAPI serve it:

```bash
# 1 — Build frontend
cd frontend
npm install
npm run build
# Output: frontend/dist/

# 2 — Build backend image (it will copy frontend/dist at runtime if ENVIRONMENT=production)
cd ..
docker build -f backend/Dockerfile -t tnboard-backend:prod .

# 3 — Run with production settings
docker run \
  -e DATABASE_URL="postgresql://..." \
  -e JWT_SECRET_KEY="..." \
  -e ENVIRONMENT="production" \
  -e CORS_ORIGINS="https://your-domain.com" \
  -e STORAGE_BACKEND="supabase" \
  -e SUPABASE_URL="https://xxx.supabase.co" \
  -e SUPABASE_SERVICE_ROLE_KEY="..." \
  -e SUPABASE_BUCKET="papers" \
  -p 8000:8000 \
  tnboard-backend:prod
```

In production mode, FastAPI serves `frontend/dist/` on all non-API paths (SPA routing).

---

## docker-compose.yml Explained

```yaml
services:
  db:          # PostgreSQL — data persisted in a named volume
  backend:     # FastAPI — reads DATABASE_URL from environment
  frontend:    # Vite dev server — proxies /api to backend:8000
```

Database URL used inside Docker Compose:
```
postgresql://tnboard:tnboard@db:5432/tnboard
```
`db` resolves to the PostgreSQL container via Docker's internal DNS.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `connection refused` on port 8000 | Backend not yet ready | Wait ~5s or check `docker compose logs backend` |
| `FATAL: database "tnboard" does not exist` | DB volume exists but schema missing | `docker compose down -v && docker compose up --build` |
| `RuntimeError: JWT_SECRET_KEY is still the insecure default` | Missing env var | Set `JWT_SECRET_KEY` in `.env` |
| Frontend shows blank page | Vite not started yet | Check `docker compose logs frontend` |
| File uploads disappear | `STORAGE_BACKEND=local` is ephemeral | Use `STORAGE_BACKEND=supabase` in production |
