# Self-Hosting Guide — TN State Board Learning Platform

A step-by-step walkthrough for setting up the project on a brand-new Windows machine, including expected output and common errors.

---

## Prerequisites to Install

| Tool       | Download                                      | Verify                   |
|------------|-----------------------------------------------|--------------------------|
| Python 3.11| https://www.python.org/downloads/             | `python --version`       |
| Node.js 20 | https://nodejs.org/                           | `node --version`         |
| Git        | https://git-scm.com/download/win              | `git --version`          |
| PostgreSQL | https://www.postgresql.org/download/windows/  | `psql --version`         |

> On Windows, ensure Python and PostgreSQL are added to `PATH` during installation.

---

## Step 1 — Clone the Repository

```cmd
git clone <your-repo-url>
cd tn-board-platform
```

**Expected output:**
```
Cloning into 'tn-board-platform'...
remote: Counting objects: ...
Resolving deltas: done.
```

**Common error:**
```
'git' is not recognized as an internal or external command
```
**Fix:** Install Git from https://git-scm.com and restart the terminal.

---

## Step 2 — Create the PostgreSQL Database

Open the PostgreSQL shell (search "psql" in Start Menu) or use `cmd`:

```cmd
psql -U postgres
```

Inside psql:
```sql
CREATE DATABASE tnboard;
CREATE USER tnboard_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE tnboard TO tnboard_user;
\q
```

**Expected output:**
```
CREATE DATABASE
CREATE ROLE
GRANT
```

**Common error:**
```
psql: error: connection to server on socket "..." failed
```
**Fix:** Start the PostgreSQL service. Open Services (Win+R → `services.msc`), find `postgresql-x64-xx`, right-click → Start.

---

## Step 3 — Configure Environment

```cmd
copy .env.example .env
notepad .env
```

Set these values in `.env`:
```
DATABASE_URL=postgresql://tnboard_user:yourpassword@localhost:5432/tnboard
JWT_SECRET_KEY=<generate below>
ENVIRONMENT=development
CORS_ORIGINS=*
STORAGE_BACKEND=local
```

Generate a secure JWT secret:
```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value for `JWT_SECRET_KEY`.

---

## Step 4 — Install Backend Dependencies

```cmd
cd backend
pip install -r requirements.txt
```

**Expected output (last few lines):**
```
Successfully installed fastapi-0.115.0 uvicorn-0.30.6 sqlalchemy-2.0.35 ...
```

**Common error:**
```
error: Microsoft Visual C++ 14.0 or greater is required
```
**Fix:** Install "Build Tools for Visual Studio" from https://visualstudio.microsoft.com/visual-cpp-build-tools/

**Common error:**
```
ERROR: Could not find a version that satisfies the requirement psycopg2-binary
```
**Fix:** Ensure PostgreSQL is installed. Then:
```cmd
pip install psycopg2-binary --no-cache-dir
```

---

## Step 5 — Seed the Database

```cmd
cd backend
python seed.py
```

**Expected output:**
```
Seeding database...
  + Class: Class 9
  + Class: Class 10
  + Class: Class 11
  + Class: Class 12
  + Subject: Class 9 — Tamil
  ...
  + Admin created: username=admin / password=admin123

Seed complete.
```

**Common error:**
```
RuntimeError: DATABASE_URL is not set.
```
**Fix:** Ensure `.env` is in the project root and `DATABASE_URL` is correctly set.

**Common error:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection refused
```
**Fix:** PostgreSQL is not running. Start the service (see Step 2).

---

## Step 6 — Change the Admin Password

**Do this before going live:**
```cmd
cd ..
python change_admin_password.py
```

Follow the prompts to set a strong password.

---

## Step 7 — Start the Backend

Open a **new terminal** (keep it open):

```cmd
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:app.main:Starting TN Board API — environment: development
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Common error:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```
**Fix:** Port 8000 is in use. Either stop the other process or use `--port 8001` and update `vite.config.js` proxy target.

Verify: Open http://localhost:8000/health — should return `{"status":"healthy"}`

---

## Step 8 — Install Frontend Dependencies

Open a **second terminal**:

```cmd
cd frontend
npm install
```

**Expected output:**
```
added 250 packages, and audited 251 packages in 15s
found 0 vulnerabilities
```

**Common error:**
```
npm : The term 'npm' is not recognized
```
**Fix:** Install Node.js from https://nodejs.org and restart the terminal.

---

## Step 9 — Start the Frontend

In the same second terminal:

```cmd
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in 191 ms

  ➜  Local:   http://localhost:5000/
  ➜  Network: http://192.168.x.x:5000/
  ➜  press h + enter to show help
```

**Common error:**
```
Error: Cannot find module '@vitejs/plugin-react'
```
**Fix:** Run `npm install` again from the `frontend/` directory.

---

## Step 10 — Open the App

| URL | Purpose |
|-----|---------|
| http://localhost:5000 | Public student portal |
| http://localhost:5000/admin/login | Admin login |
| http://localhost:8000/docs | API documentation |

---

## Step 11 — Admin Login

1. Go to http://localhost:5000/admin/login
2. Username: `admin`
3. Password: (whatever you set in Step 6; default is `admin123`)

From the admin dashboard you can upload PDFs and manage content.

---

## Possible Errors Summary

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `DATABASE_URL is not set` | Missing `.env` or wrong path | Create `.env` in project root |
| `connection refused :5432` | PostgreSQL not running | Start PostgreSQL service |
| `JWT_SECRET_KEY is insecure default` | Missing JWT key | Add a 32+ char random key to `.env` |
| `Module not found: axios` | npm install not run | `cd frontend && npm install` |
| `uvicorn: command not found` | pip install not run | `cd backend && pip install -r requirements.txt` |
| Browser: `API request failed` | Backend not running | Start uvicorn (Step 7) |
| Browser: CORS error | `CORS_ORIGINS` mismatch | Set `CORS_ORIGINS=*` in dev |
| File upload 400 error | File is not a PDF | Only PDF files are accepted |
| Upload 413 error | File too large | Check `MAX_FILE_SIZE_MB` in `.env` |
