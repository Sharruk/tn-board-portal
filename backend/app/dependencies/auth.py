import json
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from supabase import Client

from app.config.settings import get_settings
from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.supabase import get_db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────── #
# Firebase Admin SDK initialisation
#
# Two credential sources are tried, in this order:
#   1. FIREBASE_SERVICE_ACCOUNT_JSON — full SA JSON as an env-var string.
#      Preferred for Docker/Render where baking a secrets file into the image
#      is not safe or practical.
#   2. FIREBASE_SERVICE_ACCOUNT_PATH — filesystem path to the SA JSON file.
#      Useful for local development.
#
# If neither is set, Firebase Admin is NOT initialised and all protected
# endpoints will return 401 (token verification will raise an error).
# ─────────────────────────────────────────────────────────────────────────── #
settings = get_settings()


def _init_firebase() -> None:
    """Initialise Firebase Admin SDK from the best available credential."""
    if firebase_admin._apps:
        logger.info("Firebase Admin already initialised — skipping.")
        return

    # ── Strategy 1: JSON string from environment variable ────────────────
    if settings.FIREBASE_SERVICE_ACCOUNT_JSON and settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip():
        try:
            sa_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(sa_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialised from FIREBASE_SERVICE_ACCOUNT_JSON env var.")
            return
        except json.JSONDecodeError as exc:
            logger.error(
                "FIREBASE_SERVICE_ACCOUNT_JSON is set but is not valid JSON: %s", exc
            )
        except Exception as exc:
            logger.error("Failed to initialise Firebase Admin from JSON env var: %s", exc)

    # ── Strategy 2: File path ────────────────────────────────────────────
    if settings.FIREBASE_SERVICE_ACCOUNT_PATH and settings.FIREBASE_SERVICE_ACCOUNT_PATH.strip():
        try:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            logger.info(
                "Firebase Admin initialised from file: %s",
                settings.FIREBASE_SERVICE_ACCOUNT_PATH,
            )
            return
        except Exception as exc:
            logger.error(
                "Failed to initialise Firebase Admin from path '%s': %s",
                settings.FIREBASE_SERVICE_ACCOUNT_PATH,
                exc,
            )

    logger.warning(
        "Firebase Admin NOT initialised. "
        "Set FIREBASE_SERVICE_ACCOUNT_JSON (preferred) or FIREBASE_SERVICE_ACCOUNT_PATH. "
        "All protected endpoints requiring Firebase token verification will fail."
    )


_init_firebase()


async def verify_firebase_token(authorization: Annotated[str | None, Header()] = None) -> dict:
    """
    Verifies the Firebase ID token and returns the decoded token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token>.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token.",
        )


async def get_current_user(
    decoded_token: dict = Depends(verify_firebase_token),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> dict:
    """
    Retrieves the current application user from Supabase using the verified Firebase UID.
    """
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure (missing uid).",
        )

    email = decoded_token.get("email")

    # Fetch user from Supabase
    response = admin_db.table("users").select("*").eq("firebase_uid", firebase_uid).execute()
    
    # If the user doesn't exist yet, auto-create their profile with the appropriate role.
    if not response.data:
        # ── New user: auto-create a profile ─────────────────────────────
        #
        # Authorization model:
        #   - The email comes from the Firebase ID token decoded by verify_firebase_token().
        #     It is set by Google and cannot be spoofed by the client.
        #   - Only settings.ADMIN_EMAIL receives SUPER_ADMIN on first login.
        #   - Every other account receives USER (lowest privilege).
        #   - SUPER_ADMIN implicitly passes all require_role() checks.
        #
        # Note: If a stale row already exists in Supabase for this firebase_uid with
        # a non-SUPER_ADMIN role, the branch below is not reached (the existing row
        # is returned as-is). The role is NOT re-evaluated on every subsequent login,
        # which is intentional — a manually downgraded admin stays downgraded.
        role = "SUPER_ADMIN" if email == settings.ADMIN_EMAIL else "USER"

        # Auto-create the profile
        new_user = {
            "firebase_uid": firebase_uid,
            "email": email,
            "display_name": decoded_token.get("name"),
            "role": role,
            "is_active": True,
        }

        # supabase-py 2.x: .insert() returns a SyncQueryRequestBuilder that does
        # NOT support chaining .select() — call .execute() immediately, then do a
        # separate SELECT to retrieve the full row.
        try:
            insert_res = admin_db.table("users").insert(new_user).execute()
        except Exception as exc:
            # A duplicate firebase_uid means a concurrent request already created
            # this user (race condition).  Fall through to the SELECT below.
            logger.warning(
                "User insert raised an exception for firebase_uid=%s (may be duplicate): %s",
                firebase_uid,
                exc,
            )
            insert_res = None

        # If insert returned data we can use it directly; otherwise (empty data
        # or exception) do a fresh SELECT to handle the race-condition case.
        if insert_res is not None and insert_res.data:
            return insert_res.data[0]

        # Fallback: retrieve the user that now exists (either just inserted by
        # us or by a concurrent request that won the race).
        logger.info(
            "Insert returned no data for firebase_uid=%s; fetching via SELECT.",
            firebase_uid,
        )
        fetch_res = (
            admin_db.table("users")
            .select("*")
            .eq("firebase_uid", firebase_uid)
            .execute()
        )
        if fetch_res.data:
            return fetch_res.data[0]

        logger.error("Failed to create or retrieve user profile for firebase_uid=%s", firebase_uid)
        raise HTTPException(status_code=500, detail="Failed to create user profile")

    user = response.data[0]
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )
        
    return user


def require_role(allowed_roles: list[str]):
    """
    Dependency generator to restrict access to specific roles.
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        
        # SUPER_ADMIN can do everything
        if user_role == "SUPER_ADMIN":
            return current_user
            
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(allowed_roles)}.",
            )
        return current_user
    return role_checker


async def require_admin(current_user: dict = Depends(require_role(["ADMIN", "SUPER_ADMIN"]))):
    """Convenience dependency for Admin access."""
    return current_user


async def require_super_admin(current_user: dict = Depends(require_role(["SUPER_ADMIN"]))):
    """Convenience dependency for Super Admin access."""
    return current_user
