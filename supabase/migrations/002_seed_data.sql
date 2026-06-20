-- =============================================================================
-- Migration 002 — Seed Data
-- TN State Board Learning Platform
-- =============================================================================
-- Seeds the four classes and 32 subjects.
-- Exact match of backend/seed.py — verified line-by-line against the source.
-- Safe to re-run: uses INSERT … ON CONFLICT DO NOTHING throughout.
-- =============================================================================

-- ── Classes ──────────────────────────────────────────────────────────────────
-- IDs are the class numbers (9, 10, 11, 12) — intentional, not a mistake.

INSERT INTO classes (id, name, slug) VALUES
    (9,  'Class 9',  '9'),
    (10, 'Class 10', '10'),
    (11, 'Class 11', '11'),
    (12, 'Class 12', '12')
ON CONFLICT (id) DO NOTHING;


-- ── Subjects — Class 9 ───────────────────────────────────────────────────────

INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (9, 'Tamil',          'tamil',   false, 1),
    (9, 'English',        'english', false, 2),
    (9, 'Mathematics',    'maths',   false, 3),
    (9, 'Science',        'science', true,  4),
    (9, 'Social Science', 'social',  false, 5)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 10 ──────────────────────────────────────────────────────

INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (10, 'Tamil',          'tamil',   false, 1),
    (10, 'English',        'english', false, 2),
    (10, 'Mathematics',    'maths',   false, 3),
    (10, 'Science',        'science', true,  4),
    (10, 'Social Science', 'social',  false, 5)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 11 ──────────────────────────────────────────────────────

INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (11, 'Tamil',                 'tamil',     false,  1),
    (11, 'English',               'english',   false,  2),
    (11, 'Mathematics',           'maths',     false,  3),
    (11, 'Physics',               'physics',   true,   4),
    (11, 'Chemistry',             'chemistry', true,   5),
    (11, 'Biology',               'biology',   true,   6),
    (11, 'Computer Science',      'cs',        true,   7),
    (11, 'Computer Applications', 'ca',        true,   8),
    (11, 'Accountancy',           'acc',       false,  9),
    (11, 'Commerce',              'comm',      false, 10),
    (11, 'Economics',             'eco',       false, 11)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 12 ──────────────────────────────────────────────────────

INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (12, 'Tamil',                 'tamil',     false,  1),
    (12, 'English',               'english',   false,  2),
    (12, 'Mathematics',           'maths',     false,  3),
    (12, 'Physics',               'physics',   true,   4),
    (12, 'Chemistry',             'chemistry', true,   5),
    (12, 'Biology',               'biology',   true,   6),
    (12, 'Computer Science',      'cs',        true,   7),
    (12, 'Computer Applications', 'ca',        true,   8),
    (12, 'Accountancy',           'acc',       false,  9),
    (12, 'Commerce',              'comm',      false, 10),
    (12, 'Economics',             'eco',       false, 11)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Verification ─────────────────────────────────────────────────────────────
-- Run this query after applying the seed to confirm counts:
--
--   SELECT
--     (SELECT COUNT(*) FROM classes)  AS class_count,   -- expected: 4
--     (SELECT COUNT(*) FROM subjects) AS subject_count; -- expected: 32
