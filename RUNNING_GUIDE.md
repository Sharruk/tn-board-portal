# Running Guide — TN State Board Learning Platform

Complete command reference for running the project from a fresh machine.

---

## Prerequisites

| Tool       | Minimum Version | Install                              |
|------------|-----------------|--------------------------------------|
| Python     | 3.11            | https://www.python.org/downloads/    |
| Node.js    | 20              | https://nodejs.org/                  |
| npm        | 10              | Bundled with Node.js                 |
| PostgreSQL | 14              | https://www.postgresql.org/download/ |
| Git        | any             | https://git-scm.com/                 |

Or use Docker / Docker Compose to skip local installs — see `DOCKER_DEPLOYMENT.md`.

---

## Environment Setup

```bash
# Clone the repository
git clone <repo-url>
cd tn-board-platform

# Copy the environment template
cp .env.example .env
```

Open `.env` and set at minimum:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/tnboard
JWT_SECRET_KEY=<generate below>
ENVIRONMENT=development
CORS_ORIGINS=*
STORAGE_BACKEND=local
```

Generate a secure JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Backend Commands

### Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Create database (PostgreSQL)
```bash
# Create the database (run once)
createdb tnboard
# Or using psql:
psql -U postgres -c "CREATE DATABASE tnboard;"
```

### Seed initial data (run once)
```bash
cd backend
python seed.py
```
This creates:
- Classes 9, 10, 11, 12
- All subjects per class
- Default admin account (change the password immediately after)

### Change the admin password
```bash
python change_admin_password.py
```

### Start development server (with auto-reload)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Expected output:
```
INFO:app.main:Starting TN Board API — environment: development
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Start production server
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Run one-time schema migration (if upgrading from an older deployment)
```bash
cd backend
python migrate_41.py
```

---

## Frontend Commands

### Install dependencies
```bash
cd frontend
npm install
```

### Start development server (hot-reload)
```bash
cd frontend
npm run dev
```
Expected output:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5000/
  ➜  Network: http://0.0.0.0:5000/
```
The Vite dev server proxies `/api/*` and `/uploads/*` to the backend at port 8000.

### Production build
```bash
cd frontend
npm run build
```
Output goes to `frontend/dist/`. In production mode, FastAPI serves this directory directly.

### Preview the production build locally
```bash
cd frontend
npm run preview
```

---

## Running Both Services Together

Open two terminals:

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open: `http://localhost:5000`

---

## Admin Panel

URL: `http://localhost:5000/admin/login`

Login with the credentials created by `seed.py`, then immediately run:
```bash
python change_admin_password.py
```

---

## API Documentation (dev only)

Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Docker (alternative to manual setup)

```bash
# Start everything (PostgreSQL + backend + frontend)
docker compose up --build

# Run in background
docker compose up --build -d

# Stop
docker compose down

# Reset database volumes
docker compose down -v
```

See `DOCKER_DEPLOYMENT.md` for full details.
