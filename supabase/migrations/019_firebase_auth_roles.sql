-- Migration 019: Firebase Auth & Roles, Activity Tracking

-- Create Roles Enum
CREATE TYPE app_role AS ENUM ('PUBLIC', 'USER', 'CONTRIBUTOR', 'ADMIN', 'SUPER_ADMIN');

-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid TEXT UNIQUE NOT NULL,
    email TEXT,
    display_name TEXT,
    role app_role DEFAULT 'USER',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deny all via PostgREST. Backend will use service_role key to bypass RLS.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create Download Logs Table
CREATE TABLE IF NOT EXISTS download_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid TEXT NOT NULL,
    email TEXT,
    paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    downloaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deny all via PostgREST. Backend will use service_role key to bypass RLS.
ALTER TABLE download_logs ENABLE ROW LEVEL SECURITY;

-- Modify Submissions Table
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS firebase_uid TEXT,
ADD COLUMN IF NOT EXISTS verified_email TEXT;
