# AGENTS.md — AI Operating Manual
# TN Board Portal

> **Primary operating instructions for AI coding assistants working on this repository.**

---

## 1. Project Architecture & Current Tech Stack

| Layer | Technology | Deployment / Hosting |
|---|---|---|
| **Frontend** | React 18, Vite 5, Tailwind CSS | Vercel (SPA) |
| **Backend** | FastAPI 0.115, Python 3.12, Uvicorn | Vercel Serverless Functions (`api/index.py`) |
| **Database** | PostgreSQL 15, Supabase Migrations (`001`–`025`) | Supabase Database |
| **Storage** | Supabase Storage (`papers`, `submissions` buckets) | Supabase Object Storage |
| **Authentication** | Firebase Auth (Google Sign-In, Firebase ID Token) | Google Firebase / Verified by FastAPI |
| **Local Testing** | Docker (`python:3.12-slim`), pytest | Local Docker / CLI |

**Architecture Flow:**
```
Frontend (React/Vite on Vercel)
   │
   ├── Auth Flow: Firebase Auth (Google Sign-In) ──► ID Token (Bearer)
   │
   └── API Requests (Same-Origin: /api/v1/...) ──► Vercel FastAPI Serverless
                                                        │
                                                        ├── Verify Firebase ID Token
                                                        └── Supabase PostgreSQL & Storage
```

*Note: Render is decommissioned. All production traffic runs via Vercel + Supabase + Firebase.*

---

## 2. Core Rule Priorities

1. **Never Expose Secrets**: Never commit or log API keys, private keys, service account JSONs, database passwords, or `.env` files.
2. **Never Break Authentication**: Firebase Auth (Google Sign-In) + FastAPI token verification (`verify_firebase_token`) must remain intact.
3. **Never Destroy Production Data**: Never run `db reset` or destructive DDL against live databases. Retain all historical migrations (`001`–`025`).
4. **Preserve Submission & Approval Flow**: Approved papers must retain custom title, download filename, description, YouTube URL, contributor attribution, and download Content-Disposition.
5. **Keep Same-Origin API Routing**: In production, frontend API calls must route through `/api/v1/...` on the same Vercel origin.
6. **Maintain Contributor Privacy**: Never expose contributor email addresses in public API responses or pages.
7. **Verify Changes**: Run `python -m pytest` and `npm.cmd run build` before concluding tasks.

---

## 3. Git & Branching Rules

- Always verify the active branch before modifying files (`git branch --show-current`).
- Work strictly on the requested branch (e.g. `vercel-migration`).
- Do not switch branches, merge into `main`, or push to remote repositories unless explicitly instructed.

---

## 4. Verification Commands

```bash
# Backend pytest suite
cd backend && python -m pytest

# Frontend production build
cd frontend && npm.cmd run build

# Docker local backend test
docker build -t tn-board-backend ./backend
docker run --env-file ./backend/.env -p 8000:8000 tn-board-backend
```

---

## 5. Companion Documents

- [PROJECT_CONTEXT.md](file:///d:/Visual_Studio_Code/projects/tn-board-portal/.ai/PROJECT_CONTEXT.md) — Problem statement, platform features, and user journeys.
- [DEVELOPMENT_RULES.md](file:///d:/Visual_Studio_Code/projects/tn-board-portal/.ai/DEVELOPMENT_RULES.md) — Coding conventions, database migration rules, and error handling.
- [SECURITY_GUIDELINES.md](file:///d:/Visual_Studio_Code/projects/tn-board-portal/.ai/SECURITY_GUIDELINES.md) — Security standards, token verification, and data protection.
