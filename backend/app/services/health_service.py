"""
Health service — business logic for the health check.

Routes should never construct response data themselves.
All logic (even trivial logic) lives in a service so it can
be tested independently of HTTP concerns.
"""

import logging

from app.config.settings import get_settings
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)


def get_health() -> HealthResponse:
    """
    Return the application health status.

    In future sprints this can check database connectivity,
    external service availability, etc. — without changing
    the route layer at all.
    """
    settings = get_settings()
    logger.debug("Health check requested")
    return HealthResponse(status="ok", version="2.0")
