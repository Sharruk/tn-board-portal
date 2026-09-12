"""
Pydantic schemas for the Admin Activity domain.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, computed_field


class AdminActivityItem(BaseModel):
    id: str
    actor_uid: str
    actor_email: str
    actor_name: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    target_title: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime

    @computed_field
    @property
    def admin_name(self) -> str:
        return self.actor_name

    @computed_field
    @property
    def admin_email(self) -> str:
        return self.actor_email

    @computed_field
    @property
    def admin_uid(self) -> str:
        return self.actor_uid

    @computed_field
    @property
    def target_name(self) -> Optional[str]:
        return self.target_title

    @computed_field
    @property
    def details(self) -> dict[str, Any]:
        return self.metadata


class AdminActivityListResponse(BaseModel):
    data: list[AdminActivityItem]
    total: int
    limit: int
    offset: int
