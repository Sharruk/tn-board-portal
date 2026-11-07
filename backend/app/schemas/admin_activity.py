"""
Pydantic schemas for Central Admin Activity Logs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AdminActivityLogResponse(BaseModel):
    """A single administrative activity log record."""

    id: str = Field(..., description="Unique UUID identifier for the activity record")
    actor_uid: str = Field(..., description="Firebase UID of the performing administrator")
    actor_email: str = Field(..., description="Email of the performing administrator")
    actor_name: str = Field(..., description="Display name of the performing administrator")
    actor_role: str = Field(..., description="Role at time of action ('ADMIN' or 'SUPER_ADMIN')")
    action: str = Field(..., description="Standardized action identifier (e.g. 'admin.promote_user')")
    target_type: str = Field(..., description="Entity type affected (e.g. 'user', 'submission', 'paper')")
    target_id: str = Field(..., description="Identifier of the target entity")
    target_title: Optional[str] = Field(None, description="Human-readable title or summary of the target")
    reason: Optional[str] = Field(None, description="Administrative reason or justification, if provided")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe structured metadata detailing changes")
    ip_address: Optional[str] = Field(None, description="Client IP address where the action originated")
    created_at: datetime = Field(..., description="Timestamp when the action was recorded")


class AdminActivityLogListResponse(BaseModel):
    """Paginated list response for admin activity logs."""

    data: List[AdminActivityLogResponse] = Field(..., description="List of activity log records")
    total: int = Field(..., description="Total number of matching records matching the filter")
    limit: int = Field(..., description="Pagination limit applied")
    offset: int = Field(..., description="Pagination offset applied")