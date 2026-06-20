# TN State Board Learning Platform

## Overview
A Tamil Nadu State Board Question Papers & Answer Keys Portal. Students can browse question papers and answer keys for Classes 9–12 by class, subject, and exam type. Admins can upload, manage, and moderate content through a protected dashboard.

## Architecture
- **Frontend**: React 18 + Vite 5 + Tailwind CSS (SPA on port 5000)
- **Backend / DB / Auth / Storage**: Supabase (PostgreSQL, Supabase Auth, Supabase Storage)
- **No server-side backend required**: All data access goes directly from the React frontend to Supabase via RLS-protected APIs

## Key Files
- `frontend/src/` — React application source
- `frontend/src/lib/supabase.js` — Supabase client (reads VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY)
- `frontend/src/services/` — Data-access layer (papers, classes, subjects, search, admin)
- `frontend/src/contexts/AuthContext.jsx` — Auth state via Supabase Auth
- `frontend/src/pages/` — Public and admin pages
- `frontend/src/router/index.jsx` — Route definitions
- `supabase/migrations/` — SQL migrations for schema, seed data, RLS, and functions

## Required Secrets
Set these in Replit Secrets:
- `VITE_SUPABASE_URL` — your Supabase project URL (e.g. `https://xxxx.supabase.co`)
- `VITE_SUPABASE_ANON_KEY` — your Supabase anon/public key

## Running
The "Start application" workflow runs `cd frontend && npm run dev` on port 5000.

## User Preferences
- Keep the React + Supabase architecture; do not introduce a Python/Flask backend
