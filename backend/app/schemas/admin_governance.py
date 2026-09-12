"""
Admin Governance schemas.

Pydantic models for admin additions, removals, and two-person approval workflows.
Matches the live Supabase schema established in Migration 028.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, computed_field


class AdminAddRequest(BaseModel):
    """Payload for adding a trusted teacher/admin."""
    email: EmailStr = Field(..., description="Email of the user to be promoted to Admin")
    display_name: Optional[str] = Field(None, description="Optional name/title of the teacher")
    reason: Optional[str] = Field(None, description="Reason or context for adding as Admin")


class AdminRemovalRequestCreate(BaseModel):
    """Payload for requesting removal of an Admin."""
    target_uid: str = Field(..., description="Firebase UID of the Admin to be removed")
    reason: str = Field(..., min_length=5, description="Justification for removal")


class AdminGovernanceApprovalRequest(BaseModel):
    """Payload for approving or rejecting a removal request."""
    note: Optional[str] = Field(None, description="Approval or rejection notes")


class AdminGovernanceRequestResponse(BaseModel):
    """Response representing a governance request matching live schema."""
    id: str = Field(..., description="UUID primary key of request")
    request_type: str
    target_user_uid: str
    target_email: str
    target_name: str
    initiated_by_uid: str
    initiated_by_email: Optional[str] = None
    initiated_by_name: str
    status: str
    second_approver_uid: Optional[str] = None
    second_approver_email: Optional[str] = None
    second_approver_name: Optional[str] = None
    second_approved_at: Optional[datetime] = None
    decision_notes: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Compatibility aliases for frontend components
    @computed_field
    @property
    def target_uid(self) -> str:
        return self.target_user_uid

    @computed_field
    @property
    def approved_by_uid(self) -> Optional[str]:
        return self.second_approver_uid

    @computed_field
    @property
    def approved_by_name(self) -> Optional[str]:
        return self.second_approver_name

    @computed_field
    @property
    def approval_note(self) -> Optional[str]:
        return self.decision_notes

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class AdminGovernanceListResponse(BaseModel):
    """List of governance requests."""
    requests: list[AdminGovernanceRequestResponse]
    total: int


class VerifiedTeacherUpdateRequest(BaseModel):
    """Payload for granting/revoking Verified Teacher status (Super Admin only)."""
    is_verified_teacher: bool
