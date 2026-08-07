"""
GET /api/v1/health

Returns the application health status.
Route is intentionally thin — all logic lives in health_service.
"""

import logging

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import get_health

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the API health status and version. Used by Render, load balancers, and monitoring tools.",
)
async def health_check() -> HealthResponse:
    """Return API health status."""
    return get_health()
