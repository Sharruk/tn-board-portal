-- =============================================================================
-- Migration 034 — Study Materials Module
-- TN State Board Student Portal — Hungry Learner
-- =============================================================================
-- Creates the 3 core tables for the Study Materials feature:
--   1. material_categories  — Hybrid category taxonomy (Global, Class, Subject)
--   2. study_materials      — Core educational resource packages
--   3. material_files       — Multi-file attachments and external learning links
--
-- Features:
--   • PostgreSQL 17 native UNIQUE NULLS NOT DISTINCT for scoped category slugs
--   • GIN index on study_materials.tags for high-speed tag containment queries
--   • Soft-archival support on categories (is_active = false)
--   • ON DELETE RESTRICT on class_id, subject_id, and category_id to prevent scope corruption
--   • Check constraint enforcing valid category scopes
-- =============================================================================

-- ── 1. material_categories ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS material_categories (
    id            SERIAL          PRIMARY KEY,
    class_id      INTEGER         REFERENCES classes(id) ON DELETE CASCADE,
    subject_id    INTEGER         REFERENCES subjects(id) ON DELETE CASCADE,
    name          VARCHAR(100)    NOT NULL,
    slug          VARCHAR(120)    NOT NULL,
    description   TEXT,
    is_active     BOOLEAN         NOT NULL DEFAULT true,
    display_order INTEGER         NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Prevent invalid scope: a subject category cannot exist without a parent class
    CONSTRAINT chk_material_categories_scope
        CHECK (class_id IS NOT NULL OR subject_id IS NULL),

    -- Unique slug per scope (Global, Class-level, or Subject-level)
    CONSTRAINT uq_material_categories_scope_slug
        UNIQUE NULLS NOT DISTINCT (class_id, subject_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_material_categories_lookup
    ON material_categories (class_id, subject_id, is_active);

COMMENT ON TABLE  material_categories IS 'Dynamic categories for study materials (Global, Class-scoped, or Subject-scoped).';
COMMENT ON COLUMN material_categories.class_id IS 'NULL = applies to all classes (Global Category).';
COMMENT ON COLUMN material_categories.subject_id IS 'NULL = applies to all subjects in class (or Global if class_id is also NULL).';
COMMENT ON COLUMN material_categories.is_active IS 'False = archived; hidden from new upload dropdowns, preserved on existing materials.';


-- ── 2. study_materials ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS study_materials (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    title               VARCHAR(255)    NOT NULL,
    slug                VARCHAR(300)    NOT NULL UNIQUE,
    description         TEXT,
    
    -- Scope: class is mandatory; subject is NULL for class-level general resources
    class_id            INTEGER         NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
    subject_id          INTEGER         REFERENCES subjects(id) ON DELETE RESTRICT,
    
    -- Category association (NULLABLE for uncategorized drafts/resources; RESTRICT prevents accidental category deletion)
    category_id         INTEGER         REFERENCES material_categories(id) ON DELETE RESTRICT,
    
    -- Classification metadata
    medium              VARCHAR(20)     NOT NULL DEFAULT 'both'
                        CHECK (medium IN ('tamil', 'english', 'both', 'not_applicable')),
    question_formats    VARCHAR(20)[]   NOT NULL DEFAULT '{}',
    tags                TEXT[]          NOT NULL DEFAULT '{}',
    academic_year       VARCHAR(20),    -- Optional; no static hardcoded default
    
    -- Attribution
    author_name         VARCHAR(150),
    author_organization VARCHAR(200),
    
    -- Publication Lifecycle
    status              VARCHAR(20)     NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'published', 'archived')),
    
    -- Telemetry Counters
    view_count          INTEGER         NOT NULL DEFAULT 0,
    download_count      INTEGER         NOT NULL DEFAULT 0,
    
    -- Governance Audit (uses live users.id UUID type)
    created_by          UUID            REFERENCES users(id) ON DELETE SET NULL,
    updated_by          UUID            REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Question formats integrity check (empty array = not applicable)
    CONSTRAINT chk_study_materials_question_formats
        CHECK (question_formats <@ ARRAY['1_mark', '2_marks', '3_marks', '5_marks', '10_marks']::VARCHAR[])
);

CREATE INDEX IF NOT EXISTS idx_study_materials_class_subject_pub
    ON study_materials (class_id, subject_id, status) WHERE status = 'published';

CREATE INDEX IF NOT EXISTS idx_study_materials_category_pub
    ON study_materials (category_id, status) WHERE status = 'published';

CREATE INDEX IF NOT EXISTS idx_study_materials_tags
    ON study_materials USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_study_materials_status
    ON study_materials (status);

CREATE INDEX IF NOT EXISTS idx_study_materials_created_at
    ON study_materials (created_at DESC);

COMMENT ON TABLE  study_materials IS 'Core study materials, chapter notes, revision guides, and formulas.';
COMMENT ON COLUMN study_materials.subject_id IS 'NULL indicates a class-level general resource (e.g. general study timetable).';
COMMENT ON COLUMN study_materials.status IS 'draft = admin preview only; published = live on public site; archived = hidden from public.';


-- ── 3. material_files ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS material_files (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id         UUID            NOT NULL REFERENCES study_materials(id) ON DELETE CASCADE,
    file_title          VARCHAR(255)    NOT NULL,
    display_filename    VARCHAR(255)    NOT NULL,
    file_type           VARCHAR(30)     NOT NULL DEFAULT 'pdf'
                        CHECK (file_type IN ('pdf', 'image', 'word', 'presentation', 'spreadsheet', 'video', 'external_link', 'other')),
    mime_type           VARCHAR(100),
    file_size           BIGINT          NOT NULL DEFAULT 0,
    bucket_name         VARCHAR(100),
    storage_path        TEXT,
    external_url        TEXT,
    sort_order          INTEGER         NOT NULL DEFAULT 0,
    download_count      INTEGER         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Every file must have a storage object or an external URL
    CONSTRAINT chk_material_files_payload
        CHECK (
            (storage_path IS NOT NULL AND bucket_name IS NOT NULL) OR
            (external_url IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_material_files_material_id
    ON material_files (material_id, sort_order);

COMMENT ON TABLE  material_files IS 'Multi-file attachments and external resource links associated with study materials.';
COMMENT ON COLUMN material_files.storage_path IS 'Stable Supabase Storage object key (NULL for external video/links).';
COMMENT ON COLUMN material_files.external_url IS 'External resource URL (e.g. YouTube video explanation or educational applet).';


-- ── 4. Seed Standard Global Categories ───────────────────────────────────────
INSERT INTO material_categories (class_id, subject_id, name, slug, description, display_order)
VALUES
    (NULL, NULL, 'Full Guide / Complete Notes', 'full-guide', 'Comprehensive chapter notes and textbook solutions', 1),
    (NULL, NULL, 'Formula & Derivations Compendium', 'formula-sheet', 'Essential equations, mathematical formulas, and scientific derivations', 2),
    (NULL, NULL, 'Important Questions & Unit Banks', 'important-questions', 'High-frequency 2-mark, 3-mark, and 5-mark question banks with answers', 3),
    (NULL, NULL, 'PTA Question Bank Solutions', 'pta-solutions', 'Parent Teacher Association model questions and solution keys', 4),
    (NULL, NULL, 'Practical & Lab Manuals', 'lab-manual', 'Science experiments, record work, and viva guides', 5)
ON CONFLICT (class_id, subject_id, slug) DO NOTHING;


-- ── 5. Row Level Security (RLS) ───────────────────────────────────────────────
ALTER TABLE material_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_materials     ENABLE ROW LEVEL SECURITY;
ALTER TABLE material_files      ENABLE ROW LEVEL SECURITY;

-- material_categories: Active categories visible to public; full access for authenticated/admin
DROP POLICY IF EXISTS "material_categories_public_select" ON material_categories;
CREATE POLICY "material_categories_public_select" ON material_categories
    FOR SELECT TO anon, authenticated
    USING (is_active = true);

DROP POLICY IF EXISTS "material_categories_admin_all" ON material_categories;
CREATE POLICY "material_categories_admin_all" ON material_categories
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

-- study_materials: Published materials visible to public; full access for authenticated/admin
DROP POLICY IF EXISTS "study_materials_public_select" ON study_materials;
CREATE POLICY "study_materials_public_select" ON study_materials
    FOR SELECT TO anon, authenticated
    USING (status = 'published');

DROP POLICY IF EXISTS "study_materials_admin_all" ON study_materials;
CREATE POLICY "study_materials_admin_all" ON study_materials
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

-- material_files: Files of published materials visible to public; full access for authenticated/admin
DROP POLICY IF EXISTS "material_files_public_select" ON material_files;
CREATE POLICY "material_files_public_select" ON material_files
    FOR SELECT TO anon, authenticated
    USING (
        EXISTS (
            SELECT 1 FROM study_materials sm
            WHERE sm.id = material_files.material_id AND sm.status = 'published'
        )
    );

DROP POLICY IF EXISTS "material_files_admin_all" ON material_files;
CREATE POLICY "material_files_admin_all" ON material_files
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);
