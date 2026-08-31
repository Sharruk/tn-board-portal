"""
User Profile endpoints — GET /api/v1/users/me, PATCH /api/v1/users/me
                      — GET /api/v1/profile/me, PATCH /api/v1/profile/me (aliases)
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.supabase import get_db
from app.schemas.user_profile import UpdateProfileRequest, UserProfileResponse
from app.services.user_profile_service import UserProfileService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User Profile"])


@router.get(
    "/users/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and stats",
    description=(
        "Authenticated endpoint. Returns the authenticated user's profile, "
        "editable contribution name, activity stats, badge, and leaderboard position."
    ),
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Authentication required"},
    },
)
@router.get(
    "/profile/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and stats (alias)",
    include_in_schema=False,
)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Retrieve authenticated user's profile and stats."""
    service = UserProfileService(db)
    return service.get_profile(current_user)


@router.patch(
    "/users/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update public contribution name",
    description=(
        "Authenticated endpoint. Updates the user's public display/contribution name. "
        "Does NOT alter historical Firebase authentication or ownership records."
    ),
    responses={
        200: {"description": "Contribution name updated"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error (name length or invalid characters)"},
    },
)
@router.patch(
    "/profile/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update public contribution name (alias)",
    include_in_schema=False,
)
async def update_my_profile(
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update contribution display name."""
    service = UserProfileService(db)
    return service.update_display_name(current_user, req)
