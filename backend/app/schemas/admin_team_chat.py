"""
Pydantic schemas for Admin Team Group Chat.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator


class AdminGroupMessageCreateRequest(BaseModel):
    """Payload to post a new message to Admin Team Chat."""
    message: str = Field(..., min_length=1, max_length=5000, description="Message text content")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or whitespace only.")
        if len(v) > 5000:
            raise ValueError("Message exceeds maximum length of 5000 characters.")
        return cleaned


class AdminGroupMessageResponse(BaseModel):
    """A single message in the Admin Team Chat."""
    id: str
    sender_firebase_uid: str
    sender_email: str
    sender_name: str
    sender_role: str = Field(..., description="'ADMIN' or 'SUPER_ADMIN'")
    message: str
    created_at: datetime


class AdminGroupMessageListResponse(BaseModel):
    """Paginated list of Admin Team Chat messages."""
    data: List[AdminGroupMessageResponse]
    total: int
    limit: int
    offset: int

