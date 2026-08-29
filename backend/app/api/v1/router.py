"""
API v1 router — aggregates all v1 endpoint routers.

To add a new resource:
    1. Create app/api/v1/endpoints/<resource>.py
    2. Import its router here and add an include_router() call.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.classes import router as classes_router
from app.api.v1.endpoints.community import router as community_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.leaderboard import router as leaderboard_router
from app.api.v1.endpoints.papers import router as papers_router
from app.api.v1.endpoints.subjects import router as subjects_router
from app.api.v1.endpoints.submissions import router as submissions_router

router = APIRouter()

# ------------------------------------------------------------------ #
# Register endpoint routers
# ------------------------------------------------------------------ #
router.include_router(health_router)
router.include_router(classes_router)
router.include_router(subjects_router)
router.include_router(papers_router)
router.include_router(submissions_router)
router.include_router(leaderboard_router)
router.include_router(community_router)
router.include_router(analytics_router)

