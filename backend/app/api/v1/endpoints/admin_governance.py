"""
Admin Governance endpoints.

Handles:
- Delegated addition of trusted teachers/Admins
- Two-person removal request & approval workflow
- Listing governance requests
- Super Admin grant/revocation of Verified Teacher status
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import (
    require_admin,
    require_super_admin,
    require_verified_teacher,
)
from app.dependencies.supabase import get_db
from app.schemas.admin_governance import (
    AdminAddRequest,
    AdminGovernanceApprovalRequest,
    AdminGovernanceListResponse,
    AdminRemovalRequestCreate,
    VerifiedTeacherUpdateRequest,
)
from app.services.admin_governance_service import AdminGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Governance"])


@router.post(
    "/governance/add",
    status_code=status.HTTP_200_OK,
    summary="Add an Administrator (Super Admin or Verified Teacher)",
    description="Super Admin or Verified Teacher adds a trusted educator to the Administrator network (max 3/month for Verified Teachers).",
)
async def add_admin(
    req: AdminAddRequest,
    current_user: dict = Depends(require_verified_teacher),
    db: Session = Depends(get_db),
) -> dict:
    """Add a new Admin."""
    service = AdminGovernanceService(db)
    return service.add_admin(req=req, initiator=current_user)


@router.post(
    "/governance/removal-request",
    status_code=status.HTTP_200_OK,
    summary="Request Admin removal (Verified Teacher or Super Admin)",
    description="Request removal of an Admin. Unilateral for Super Admin; requires second approval if initiated by Verified Teacher.",
)
async def request_admin_removal(
    req: AdminRemovalRequestCreate,
    current_user: dict = Depends(require_verified_teacher),
    db: Session = Depends(get_db),
) -> dict:
    """Initiate an Admin removal request."""
    service = AdminGovernanceService(db)
    return service.request_admin_removal(req=req, initiator=current_user)


@router.get(
    "/governance/requests",
    response_model=AdminGovernanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List governance requests",
    description="Admin or Super Admin reviews pending/history of governance requests.",
)
async def list_governance_requests(
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    request_type: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminGovernanceListResponse:
    """List governance requests."""
    service = AdminGovernanceService(db)
    return service.list_governance_requests(
        status=status_filter,
        request_type=request_type,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/governance/requests/{request_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve governance removal request (Verified Teacher or Super Admin)",
    description="Approve removal request (second Verified Teacher or Super Admin). Initiator and target cannot approve.",
)
async def approve_governance_request(
    request_id: Annotated[str, Path(description="UUID of the governance request")],
    req: Optional[AdminGovernanceApprovalRequest] = None,
    current_user: dict = Depends(require_verified_teacher),
    db: Session = Depends(get_db),
) -> dict:
    """Approve governance removal request."""
    service = AdminGovernanceService(db)
    note = req.note if req else None
    return service.process_removal_approval(
        request_id=request_id,
        action="APPROVED",
        approver=current_user,
        note=note,
    )


@router.post(
    "/governance/requests/{request_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject governance removal request (Verified Teacher or Super Admin)",
    description="Reject removal request.",
)
async def reject_governance_request(
    request_id: Annotated[str, Path(description="UUID of the governance request")],
    req: Optional[AdminGovernanceApprovalRequest] = None,
    current_user: dict = Depends(require_verified_teacher),
    db: Session = Depends(get_db),
) -> dict:
    """Reject governance removal request."""
    service = AdminGovernanceService(db)
    note = req.note if req else None
    return service.process_removal_approval(
        request_id=request_id,
        action="REJECTED",
        approver=current_user,
        note=note,
    )


@router.patch(
    "/users/{firebase_uid}/verified-teacher",
    status_code=status.HTTP_200_OK,
    summary="Update Verified Teacher status (Super Admin only)",
    description="Super Admin grants or revokes Verified Teacher status for an Administrator.",
)
async def update_verified_teacher_status(
    firebase_uid: Annotated[str, Path()],
    req: VerifiedTeacherUpdateRequest,
    current_user: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Grant/revoke Verified Teacher status."""
    service = AdminGovernanceService(db)
    return service.toggle_verified_teacher(
        target_uid=firebase_uid,
        is_verified=req.is_verified_teacher,
        current_user=current_user,
    )
