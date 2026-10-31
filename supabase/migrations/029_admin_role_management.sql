-- =============================================================================
-- Migration 029 — Super Admin & Admin Role Management & Secure Pre-authorization
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Users: Add previous_role column to safely preserve original role (USER/CONTRIBUTOR)
--      when promoted to Admin, restoring it upon revocation.
--   2. Pending Admin Appointments: Table for pre-authorizing Google account emails as Admins.
--   3. Atomic Claim Stored Procedure: claim_pending_admin_appointment() with strict
--      security constraints, account linking validation, and race condition prevention.
--   4. RLS & Permissions: Restrict execution to service_role with explicit search_path.
--
-- Safe to re-run: Uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS throughout.
-- Backward Compatible: YES
-- =============================================================================

-- ── 1. Users Table Enhancements ──────────────────────────────────────────────
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS previous_role app_role DEFAULT NULL;

COMMENT ON COLUMN public.users.previous_role IS 'Original user role (USER or CONTRIBUTOR) prior to Admin promotion, restored upon Admin revocation.';

CREATE INDEX IF NOT EXISTS idx_users_email_lower ON public.users (LOWER(email));


-- ── 2. Pending Admin Appointments Table (Method 2) ───────────────────────────
CREATE TABLE IF NOT EXISTS public.pending_admin_appointments (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT         NOT NULL,
    normalized_email  TEXT         NOT NULL,
    created_by_uid    TEXT         NOT NULL,
    created_by_email  TEXT         NOT NULL,
    status            VARCHAR(20)  NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'revoked')),
    claimed_at        TIMESTAMPTZ  NULL,
    claimed_by_uid    TEXT         NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Unique index ensuring at most ONE active pending pre-authorization per email
CREATE UNIQUE INDEX IF NOT EXISTS idx_uq_pending_admin_norm_email 
    ON public.pending_admin_appointments (normalized_email) 
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_pending_admin_status 
    ON public.pending_admin_appointments (status);

COMMENT ON TABLE public.pending_admin_appointments IS 'Pre-authorized Admin invitations for Google accounts created by Super Admin.';


-- ── 3. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE public.pending_admin_appointments ENABLE ROW LEVEL SECURITY;

-- Block direct PostgREST client queries; accessed solely via trusted backend / service_role
DROP POLICY IF EXISTS "pending_admin_deny_client" ON public.pending_admin_appointments;
CREATE POLICY "pending_admin_deny_client" ON public.pending_admin_appointments FOR ALL TO public USING (false);


-- ── 4. Atomic Appointment Claim Function (SECURITY DEFINER) ──────────────────
CREATE OR REPLACE FUNCTION public.claim_pending_admin_appointment(
    p_firebase_uid TEXT,
    p_email TEXT,
    p_display_name TEXT,
    p_photo_url TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_norm_email TEXT := LOWER(TRIM(p_email));
    v_appt RECORD;
    v_existing_by_uid RECORD;
    v_existing_by_email RECORD;
    v_user RECORD;
    v_target_role app_role := 'USER';
BEGIN
    -- Security Check 1: Account takeover prevention
    -- Check if a user already exists with this email under a DIFFERENT Firebase UID
    SELECT * INTO v_existing_by_email 
    FROM public.users 
    WHERE LOWER(email) = v_norm_email 
      AND firebase_uid <> p_firebase_uid;

    IF FOUND THEN
        RAISE EXCEPTION 'ACCOUNT_CONFLICT: Email % is already registered to a different account identifier.', p_email;
    END IF;

    -- Fetch user by firebase_uid if already present
    SELECT * INTO v_existing_by_uid 
    FROM public.users 
    WHERE firebase_uid = p_firebase_uid;

    -- Determine target role
    IF v_norm_email = 'hungrylearner786@gmail.com' THEN
        v_target_role := 'SUPER_ADMIN';
    ELSE
        -- Atomically claim pending appointment using row-lock update
        UPDATE public.pending_admin_appointments
        SET status = 'claimed',
            claimed_at = NOW(),
            claimed_by_uid = p_firebase_uid,
            updated_at = NOW()
        WHERE normalized_email = v_norm_email
          AND status = 'pending'
        RETURNING * INTO v_appt;

        IF FOUND THEN
            v_target_role := 'ADMIN';
        ELSIF v_existing_by_uid IS NOT NULL AND v_existing_by_uid.role IN ('ADMIN', 'SUPER_ADMIN') THEN
            -- Preserve existing admin role
            v_target_role := v_existing_by_uid.role;
        ELSIF v_existing_by_uid IS NOT NULL THEN
            v_target_role := v_existing_by_uid.role;
        ELSE
            v_target_role := 'USER';
        END IF;
    END IF;

    -- Upsert user record safely
    INSERT INTO public.users (
        firebase_uid, email, display_name, role, is_active, photo_url, last_active_at, created_at, updated_at
    )
    VALUES (
        p_firebase_uid, p_email, p_display_name, v_target_role, true, p_photo_url, NOW(), NOW(), NOW()
    )
    ON CONFLICT (firebase_uid) DO UPDATE
    SET 
        email = EXCLUDED.email,
        photo_url = COALESCE(EXCLUDED.photo_url, users.photo_url),
        last_active_at = NOW(),
        updated_at = NOW(),
        role = CASE 
            WHEN v_target_role = 'ADMIN' AND users.role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN 'ADMIN'::app_role
            WHEN v_target_role = 'SUPER_ADMIN' THEN 'SUPER_ADMIN'::app_role
            ELSE users.role 
        END,
        previous_role = CASE
            WHEN v_target_role = 'ADMIN' AND users.role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN users.role
            ELSE users.previous_role
        END
    RETURNING * INTO v_user;

    RETURN to_jsonb(v_user);
END;
$$;


-- ── 5. Permissions & Grants ──────────────────────────────────────────────────
-- Revoke all execute on claim function from public/anon/authenticated
REVOKE EXECUTE ON FUNCTION public.claim_pending_admin_appointment(TEXT, TEXT, TEXT, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_pending_admin_appointment(TEXT, TEXT, TEXT, TEXT) TO service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.pending_admin_appointments TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.users TO service_role;


-- ── 6. Initial Super Admin Database Guarantee ────────────────────────────────
UPDATE public.users 
SET role = 'SUPER_ADMIN' 
WHERE LOWER(email) = 'hungrylearner786@gmail.com';

