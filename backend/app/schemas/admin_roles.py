"""
Pydantic schemas for Super Admin & Admin Role Management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class AdminMeResponse(BaseModel):
    """Authenticated administrator identity and verified privileges."""
    id: str
    firebase_uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    is_super_admin: bool


class AdminAccountItem(BaseModel):
    """Administrator profile item for Admin list."""
    id: str
    firebase_uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    previous_role: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None


class AdminListResponse(BaseModel):
    """Response containing list of all active administrators."""
    data: List[AdminAccountItem]
    total: int


class PendingAppointmentItem(BaseModel):
    """Pending pre-authorized Admin appointment item."""
    id: str
    email: str
    normalized_email: str
    created_by_uid: str
    created_by_email: str
    status: str
    created_at: datetime


class PendingAppointmentListResponse(BaseModel):
    """Response containing list of pending pre-authorized Admin appointments."""
    data: List[PendingAppointmentItem]
    total: int


class PreauthorizeAdminRequest(BaseModel):
    """Payload to pre-authorize a Google account email as an Admin."""
    email: EmailStr = Field(..., description="Google account email address to pre-authorize")


class PromoteUserRequest(BaseModel):
    """Payload to promote an existing registered user to Admin."""
    firebase_uid: str = Field(..., min_length=1, description="Firebase UID of the registered user to promote")


class AdminRoleActionResponse(BaseModel):
    """Standard response for admin role promotion, appointment, or revocation."""
    success: bool
    message: str
    user: Optional[AdminAccountItem] = None

