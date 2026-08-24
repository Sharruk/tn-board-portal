"""
Leaderboard endpoint — public rankings for active contributors.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from app.db.supabase_client import get_supabase_admin_client
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get(
    "",
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
async def get_leaderboard(
    limit: Annotated[int, Query(description="Max contributors to return", ge=1, le=100)] = 50,
    db: Client = Depends(get_supabase_admin_client),
) -> LeaderboardResponse:
    """Retrieve public contributor rankings."""
    service = LeaderboardService(db)
    return service.get_leaderboard(limit=limit)
