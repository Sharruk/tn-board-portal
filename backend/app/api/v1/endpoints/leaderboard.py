"""
Leaderboard endpoint — public rankings for active contributors.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.supabase import get_db
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(tags=["Leaderboard"])


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get contributor leaderboard",
    description=(
        "Public endpoint. Returns rankings of contributors based on accepted contributions "
        "and acceptance rates. No authentication required."
    ),
    responses={
        200: {"description": "Ranked list of contributors"},
    },
)
@router.get(
    "/contributors",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get contributor leaderboard (alias)",
    description=(
        "Public endpoint alias for /leaderboard. Returns rankings of contributors based on accepted contributions "
        "and acceptance rates. No authentication required."
    ),
    responses={
        200: {"description": "Ranked list of contributors"},
    },
)
async def get_leaderboard(
    limit: Annotated[int, Query(description="Max contributors to return", ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    """Retrieve public contributor rankings."""
    service = LeaderboardService(db)
    return service.get_leaderboard(limit=limit)

