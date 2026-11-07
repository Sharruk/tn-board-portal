-- =============================================================================
-- Migration 031: Admin Appointment Claim Concurrency and Identity Safety
-- =============================================================================
-- Description:
--   Hardens admin appointment claim concurrency, email identity uniqueness,
--   and role-transition safety:
--   1. Preflight assertion ensuring zero duplicate normalized emails exist.
--   2. Creates partial unique index on LOWER(TRIM(email)) in public.users.
--   3. Replaces public.claim_pending_admin_appointment with:
--      - Strict parameter validation (rejects NULL/blank UID and email before locking).
--      - Transaction-level advisory lock serializing claims on normalized email.
--      - Canonical LOWER(TRIM(email)) normalization across conflict check, lookup, and upsert.
--      - Scalar role lookup using FOUND to eliminate composite RECORD nullability traps.
--      - Explicit NULL-safe role transitions and repair in ON CONFLICT DO UPDATE.
--      - Structured JSONB envelope return payload (user, claimed, appointment_id, assigned_role).
--   4. Explicit execution permissions: revoked from PUBLIC/anon/authenticated, granted to service_role.
-- =============================================================================

-- Step 1: Pre-flight check: ensure zero duplicate normalized emails exist
DO $$
DECLARE
    v_dup_count INT;
BEGIN
    SELECT COUNT(*) INTO v_dup_count
    FROM (
        SELECT LOWER(TRIM(email))
        FROM public.users
        WHERE email IS NOT NULL AND TRIM(email) != ''
        GROUP BY LOWER(TRIM(email))
        HAVING COUNT(*) > 1
    ) dupes;

    IF v_dup_count > 0 THEN
        RAISE EXCEPTION 'MIGRATION_HALTED: Found % duplicate normalized email groups in public.users. Manual resolution required before applying unique index.', v_dup_count;
    END IF;
END $$;

-- Step 2: Create partial unique index on canonical normalized email
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_unique_email_lower
ON public.users (LOWER(TRIM(email)))
WHERE email IS NOT NULL AND TRIM(email) != '';

-- Step 3: Replace claim function with identity-safe, concurrency-hardened implementation
CREATE OR REPLACE FUNCTION public.claim_pending_admin_appointment(
    p_firebase_uid TEXT,
    p_email TEXT,
    p_display_name TEXT,
    p_photo_url TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    v_norm_email TEXT;
    v_claimed BOOLEAN := FALSE;
    v_claimed_appt_id TEXT := NULL;
    v_assigned_role TEXT := NULL;
    v_existing_uid_found BOOLEAN := FALSE;
    v_existing_role public.app_role := NULL;
    v_user RECORD;
    v_target_role public.app_role := 'USER';
BEGIN
    -- Guard 1: Immediate parameter validation before acquiring locks
    IF p_firebase_uid IS NULL OR TRIM(p_firebase_uid) = '' THEN
        RAISE EXCEPTION 'INVALID_UID: Firebase UID parameter is required and cannot be empty.';
    END IF;

    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        RAISE EXCEPTION 'INVALID_EMAIL: Email parameter is required and cannot be empty or whitespace-only.';
    END IF;

    -- Canonical normalization applied once upfront
    v_norm_email := LOWER(TRIM(p_email));

    -- Guard 2: Transaction-level advisory lock serializing operations on normalized email
    PERFORM pg_advisory_xact_lock(hashtext(v_norm_email));

    -- Guard 3: Account takeover prevention (Matches canonical LOWER(TRIM(email)))
    PERFORM 1 FROM public.users
    WHERE LOWER(TRIM(email)) = v_norm_email
      AND firebase_uid <> p_firebase_uid;

    IF FOUND THEN
        RAISE EXCEPTION 'ACCOUNT_CONFLICT: Email % is already registered to a different account identifier.', p_email;
    END IF;

    -- Step 1: Scalar role lookup by UID (eliminates composite RECORD nullability trap)
    SELECT role INTO v_existing_role
    FROM public.users
    WHERE firebase_uid = p_firebase_uid;
    v_existing_uid_found := FOUND;

    -- Step 2: Determine target role and attempt atomic appointment claim
    IF v_norm_email = 'hungrylearner786@gmail.com' THEN
        v_target_role := 'SUPER_ADMIN';
    ELSE
        UPDATE public.pending_admin_appointments
        SET status = 'claimed',
            claimed_at = NOW(),
            claimed_by_uid = p_firebase_uid,
            updated_at = NOW()
        WHERE normalized_email = v_norm_email
          AND status = 'pending'
        RETURNING id::text INTO v_claimed_appt_id;

        IF FOUND THEN
            v_claimed := TRUE;
            v_assigned_role := 'ADMIN';
            v_target_role := 'ADMIN';
        ELSIF v_existing_uid_found AND v_existing_role IN ('ADMIN', 'SUPER_ADMIN') THEN
            v_target_role := v_existing_role;
        ELSIF v_existing_uid_found AND v_existing_role IS NOT NULL THEN
            -- Defensive: Preserve existing role only if not null
            v_target_role := v_existing_role;
        ELSE
            -- Default to USER for new accounts or corrupted NULL roles
            v_target_role := 'USER';
        END IF;
    END IF;

    -- Step 3: Upsert user record with explicit NULL-safe role transitions
    INSERT INTO public.users (
        firebase_uid, email, display_name, role, is_active, photo_url, last_active_at, created_at, updated_at
    )
    VALUES (
        p_firebase_uid, v_norm_email, p_display_name, v_target_role, true, p_photo_url, NOW(), NOW(), NOW()
    )
    ON CONFLICT (firebase_uid) DO UPDATE
    SET
        email = EXCLUDED.email,
        photo_url = COALESCE(EXCLUDED.photo_url, users.photo_url),
        last_active_at = NOW(),
        updated_at = NOW(),
        role = CASE
            -- Super Admin assignment
            WHEN v_target_role = 'SUPER_ADMIN' THEN 'SUPER_ADMIN'::public.app_role

            -- Promotion to ADMIN: handles users.role IS NULL explicitly
            WHEN v_target_role = 'ADMIN' AND (users.role IS NULL OR users.role NOT IN ('ADMIN'::public.app_role, 'SUPER_ADMIN'::public.app_role)) THEN 'ADMIN'::public.app_role

            -- Preserve existing ADMIN or SUPER_ADMIN (no accidental downgrade)
            WHEN users.role IN ('ADMIN'::public.app_role, 'SUPER_ADMIN'::public.app_role) THEN users.role

            -- Defensive repair of legacy NULL role to USER if no appointment claimed
            WHEN users.role IS NULL THEN 'USER'::public.app_role

            -- Fallback preserves existing valid role
            ELSE users.role
        END,
        previous_role = CASE
            -- Record previous role on promotion, coalescing NULL to USER
            WHEN v_target_role = 'ADMIN' AND (users.role IS NULL OR users.role NOT IN ('ADMIN'::public.app_role, 'SUPER_ADMIN'::public.app_role)) THEN COALESCE(users.role, 'USER'::public.app_role)

            -- Preserve existing previous_role
            ELSE users.previous_role
        END
    RETURNING * INTO v_user;

    -- Step 4: Return structured JSON envelope
    RETURN jsonb_build_object(
        'user', to_jsonb(v_user),
        'claimed', v_claimed,
        'appointment_id', v_claimed_appt_id,
        'assigned_role', v_assigned_role
    );
END;
$$;

-- Step 5: Restrict function execution strictly to backend service_role
REVOKE ALL ON FUNCTION public.claim_pending_admin_appointment(TEXT, TEXT, TEXT, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_pending_admin_appointment(TEXT, TEXT, TEXT, TEXT) TO service_role;