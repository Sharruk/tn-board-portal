-- =============================================================================
-- Migration 001 — Schema
-- TN State Board Learning Platform
-- =============================================================================
-- Run this first. Creates all tables, constraints, and indexes.
-- Safe to re-run: uses IF NOT EXISTS / CREATE OR REPLACE throughout.
-- =============================================================================

-- ── classes ──────────────────────────────────────────────────────────────────
-- Stores the four school classes: 9, 10, 11, 12.
-- id is the class number itself (not a surrogate key) so URLs stay readable.

CREATE TABLE IF NOT EXISTS classes (
    id            INTEGER      PRIMARY KEY,          -- 9, 10, 11, 12
    name          VARCHAR(20)  NOT NULL,             -- "Class 9" … "Class 12"
    slug          VARCHAR(10)  NOT NULL UNIQUE       -- "9" … "12"
);

CREATE INDEX IF NOT EXISTS idx_classes_slug ON classes (slug);

COMMENT ON TABLE  classes          IS 'Tamil Nadu State Board school classes (9–12).';
COMMENT ON COLUMN classes.id       IS 'Class number used as primary key (9, 10, 11, 12).';
COMMENT ON COLUMN classes.slug     IS 'URL-safe identifier, matches class number.';


-- ── subjects ─────────────────────────────────────────────────────────────────
-- Each subject belongs to one class.
-- display_order controls the order shown in the UI.

CREATE TABLE IF NOT EXISTS subjects (
    id             SERIAL       PRIMARY KEY,
    class_id       INTEGER      NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name           VARCHAR(100) NOT NULL,            -- "Mathematics", "Physics", …
    slug           VARCHAR(50)  NOT NULL,            -- "maths", "physics", …
    is_practical   BOOLEAN      NOT NULL DEFAULT false,
    display_order  INTEGER      NOT NULL DEFAULT 0,

    CONSTRAINT uq_subjects_class_slug UNIQUE (class_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_subjects_class_id ON subjects (class_id);

COMMENT ON TABLE  subjects               IS 'Subjects offered per class.';
COMMENT ON COLUMN subjects.slug          IS 'Short URL-safe identifier, unique within a class.';
COMMENT ON COLUMN subjects.is_practical  IS 'True for lab/practical subjects (Physics, Chemistry, Biology, CS, CA).';
COMMENT ON COLUMN subjects.display_order IS 'Ascending display order within a class.';


-- ── papers ───────────────────────────────────────────────────────────────────
-- Core content table. Each row is one PDF (question paper or answer key).
-- public_url is the Supabase Storage CDN URL — used directly by the browser.
-- file_path is the storage object key — used for deletion.

CREATE TABLE IF NOT EXISTS papers (
    id              SERIAL        PRIMARY KEY,
    subject_id      INTEGER       NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    exam_type       VARCHAR(100)  NOT NULL,   -- "Annual Exam", "Quarterly Exam", …
    year            INTEGER       NOT NULL,
    title           VARCHAR(255)  NOT NULL,
    paper_type      VARCHAR(20)   NOT NULL    -- "question" | "answer_key"
                    CHECK (paper_type IN ('question', 'answer_key')),
    file_path       VARCHAR(500),             -- Supabase Storage object key (UUID.pdf)
    public_url      TEXT,                     -- Supabase Storage CDN public URL
    youtube_url     TEXT,                     -- Optional YouTube video embed
    is_visible      BOOLEAN       NOT NULL DEFAULT true,
    download_count  INTEGER       NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_papers_subject_title_year_exam
        UNIQUE (subject_id, title, year, exam_type)
);

CREATE INDEX IF NOT EXISTS idx_papers_subject_id   ON papers (subject_id);
CREATE INDEX IF NOT EXISTS idx_papers_is_visible   ON papers (is_visible);
CREATE INDEX IF NOT EXISTS idx_papers_created_at   ON papers (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_papers_download_cnt ON papers (download_count DESC);
CREATE INDEX IF NOT EXISTS idx_papers_exam_type    ON papers (exam_type);
CREATE INDEX IF NOT EXISTS idx_papers_year         ON papers (year);

COMMENT ON TABLE  papers              IS 'Uploaded question papers and answer keys.';
COMMENT ON COLUMN papers.paper_type   IS '"question" = question paper, "answer_key" = answer/solution.';
COMMENT ON COLUMN papers.file_path    IS 'Supabase Storage object key — used only for deletion. Not a public URL.';
COMMENT ON COLUMN papers.public_url   IS 'Supabase Storage public CDN URL — used by the browser to view/download the PDF.';
COMMENT ON COLUMN papers.is_visible   IS 'When false, paper is hidden from public view but retained for admin.';


-- ── audit_logs ───────────────────────────────────────────────────────────────
-- Records every admin action: upload, edit, delete, login.
-- admin_id references the Supabase Auth user (UUID), not a local admins table.
-- admin_email is a denormalised copy retained even if the Auth user is deleted.

CREATE TABLE IF NOT EXISTS audit_logs (
    id               SERIAL        PRIMARY KEY,
    admin_id         UUID          REFERENCES auth.users(id) ON DELETE SET NULL,
    admin_email      VARCHAR(255),
    action           VARCHAR(50)   NOT NULL,   -- "upload", "bulk_upload", "edit", "delete", "login"
    target_paper_id  INTEGER       REFERENCES papers(id) ON DELETE SET NULL,
    target_details   JSONB,                    -- Arbitrary JSON payload (title, changes, …)
    ip_address       VARCHAR(45),              -- IPv4 or IPv6 of the admin at time of action
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action     ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id   ON audit_logs (admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at DESC);

COMMENT ON TABLE  audit_logs                 IS 'Immutable admin action history.';
COMMENT ON COLUMN audit_logs.admin_id        IS 'auth.users.id — NULL if the user was deleted.';
COMMENT ON COLUMN audit_logs.admin_email     IS 'Denormalised email, retained after user deletion.';
COMMENT ON COLUMN audit_logs.target_details  IS 'JSONB payload: {"title": "…", "changes": {…}}.';


-- ── search_queries ───────────────────────────────────────────────────────────
-- Replaces the in-memory analytics.py deque/dict.
-- Every search writes one row. Aggregated in the admin dashboard.

CREATE TABLE IF NOT EXISTS search_queries (
    id            SERIAL        PRIMARY KEY,
    term          VARCHAR(255)  NOT NULL,
    result_count  INTEGER       NOT NULL DEFAULT 0,
    searched_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_queries_term        ON search_queries (term);
CREATE INDEX IF NOT EXISTS idx_search_queries_searched_at ON search_queries (searched_at DESC);

COMMENT ON TABLE  search_queries             IS 'Every search performed by a public user — replaces in-memory analytics.';
COMMENT ON COLUMN search_queries.term        IS 'Raw search term as typed by the user (not normalised).';
COMMENT ON COLUMN search_queries.result_count IS 'Number of papers returned for this search.';
