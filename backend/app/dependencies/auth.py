import json
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
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
    db: Session = Depends(get_db),
) -> dict:
    """
    Retrieves the current application user from PostgreSQL using the verified Firebase UID.
    """
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure (missing uid).",
        )

    email = decoded_token.get("email")

    # Fetch user from PostgreSQL
    stmt = text(
        "SELECT id, firebase_uid, email, display_name, role, is_active, created_at FROM users WHERE firebase_uid = :uid"
    )
    row = db.execute(stmt, {"uid": firebase_uid}).fetchone()

    # If the user doesn't exist yet, auto-create their profile with the appropriate role.
    if not row:
        role = "SUPER_ADMIN" if email == settings.ADMIN_EMAIL else "USER"
        display_name = decoded_token.get("name")
        ins_stmt = text(
            """
            INSERT INTO users (firebase_uid, email, display_name, role, is_active)
            VALUES (:uid, :email, :display_name, :role, true)
            ON CONFLICT (firebase_uid) DO NOTHING
            RETURNING id, firebase_uid, email, display_name, role, is_active, created_at
            """
        )
        try:
            ins_res = db.execute(
                ins_stmt,
                {"uid": firebase_uid, "email": email, "display_name": display_name, "role": role},
            )
            db.commit()
            row = ins_res.fetchone()
        except Exception as exc:
            db.rollback()
            logger.warning("User insert exception for firebase_uid=%s: %s", firebase_uid, exc)
            row = None

        if not row:
            row = db.execute(stmt, {"uid": firebase_uid}).fetchone()

        if not row:
            logger.error("Failed to create or retrieve user profile for firebase_uid=%s", firebase_uid)
            raise HTTPException(status_code=500, detail="Failed to create user profile")

    user = dict(row._mapping)

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


get_current_admin = require_admin


async def require_super_admin(current_user: dict = Depends(require_role(["SUPER_ADMIN"]))):
    """Convenience dependency for Super Admin access."""
    return current_user


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> dict | None:
    """Optional user dependency — returns user dict if valid Bearer token, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.removeprefix("Bearer ").strip()
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded.get("uid")
        if not uid:
            return None
        stmt = text("SELECT id, firebase_uid, email, display_name, role FROM users WHERE firebase_uid = :uid")
        row = db.execute(stmt, {"uid": uid}).fetchone()
        return dict(row._mapping) if row else {"firebase_uid": uid, "display_name": decoded.get("name")}
    except Exception:
        return None

