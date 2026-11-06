"""
Admin Roles & Pre-authorization Endpoints.
All role modification operations are strictly protected by require_super_admin.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.dependencies.auth import (
    get_current_user,
    require_admin,
    require_super_admin,
    verify_firebase_token,
)
from app.dependencies.supabase import get_db
from app.schemas.admin_roles import (
    AdminListResponse,
    AdminMeResponse,
    AdminRoleActionResponse,
    PendingAppointmentListResponse,
    PreauthorizeAdminRequest,
    PromoteUserRequest,
)
from app.repositories.admin_roles_repository import AccountConflictError
from app.services.admin_roles_service import AdminRolesService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Roles"])


@router.get(
    "/admin/me",
    response_model=AdminMeResponse,
    summary="Get current administrator profile, verified role, and Super Admin status",
    description="Endpoint for Admin Portal authentication. Claims any pending pre-authorization on login and verifies role.",
)
def get_admin_me(
    request: Request,
    decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
):
    """
    Dedicated Admin Portal identity & claim resolver.
    Claims any pending pre-authorization atomically on Admin login without impacting public user routes.
    """
    service = AdminRolesService(db)

    # 1. Resolve and claim any pending appointment for this verified Google identity
    # Safely extract client IP from peer connection without trusting arbitrary client headers
    client_ip = request.client.host if request.client else None

    try:
        user = service.resolve_and_claim_admin(decoded_token, ip_address=client_ip)
    except AccountConflictError as exc:
        # Account takeover or conflict detected
        logger.error("Admin account linking conflict: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # 2. Verify administrative access
    user_role = user.get("role")
    if user_role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted. Account does not have administrative privileges.",
        )

    # 3. Verify active status: disabled accounts cannot access admin routes
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    return service.get_admin_me(user)


@router.get(
    "/admin/roles/admins",
    response_model=AdminListResponse,
    summary="List all active administrators (Super Admin only)",
)
def list_admins(
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Retrieve list of all active administrators (Super Admin and Admins)."""
    service = AdminRolesService(db)
    return service.get_admins_list()


@router.get(
    "/admin/roles/pending",
    response_model=PendingAppointmentListResponse,
    summary="List all pending email pre-authorizations (Super Admin only)",
)
def list_pending_appointments(
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Retrieve list of all pending pre-authorized admin appointments."""
    service = AdminRolesService(db)
    return service.get_pending_appointments()


@router.post(
    "/admin/roles/preauthorize",
    response_model=AdminRoleActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pre-authorize an email address as Admin (Method 2 — Super Admin only)",
)
def preauthorize_admin(
    req: PreauthorizeAdminRequest,
    request: Request,
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Record an email address as pre-authorized for Admin access upon first Google Sign-In."""
    client_ip = request.client.host if request.client else None
    service = AdminRolesService(db)
    return service.preauthorize_email(req.email, current_user, ip_address=client_ip)


@router.delete(
    "/admin/roles/pending/{appointment_id}",
    response_model=AdminRoleActionResponse,
    summary="Revoke a pending email pre-authorization (Super Admin only)",
)
def revoke_pending_appointment(
    appointment_id: str,
    request: Request,
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Cancel an active pending pre-authorization before the user completes first sign-in."""
    client_ip = request.client.host if request.client else None
    service = AdminRolesService(db)
    return service.revoke_pending_appointment(
        appointment_id,
        current_user=current_user,
        ip_address=client_ip,
    )


@router.post(
    "/admin/roles/promote-user",
    response_model=AdminRoleActionResponse,
    summary="Promote an existing registered user to Admin (Method 1 — Super Admin only)",
)
def promote_user(
    req: PromoteUserRequest,
    request: Request,
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Assign ADMIN role to an existing registered user, preserving their previous role."""
    client_ip = request.client.host if request.client else None
    service = AdminRolesService(db)
    return service.promote_registered_user(req.firebase_uid, current_user, ip_address=client_ip)


@router.delete(
    "/admin/roles/revoke/{firebase_uid}",
    response_model=AdminRoleActionResponse,
    summary="Revoke an Admin's privileges (Super Admin only)",
)
def revoke_admin(
    firebase_uid: str,
    request: Request,
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Revoke an Admin's administrative role and safely restore their previous role."""
    client_ip = request.client.host if request.client else None
    service = AdminRolesService(db)
    return service.revoke_admin_role(firebase_uid, current_user, ip_address=client_ip)
