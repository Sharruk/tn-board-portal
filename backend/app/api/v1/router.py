"""
API v1 router — aggregates all v1 endpoint routers.

To add a new resource:
    1. Create app/api/v1/endpoints/<resource>.py
    2. Import its router here and add an include_router() call.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router

router = APIRouter()

# ------------------------------------------------------------------ #
# Register endpoint routers
# ------------------------------------------------------------------ #
router.include_router(health_router)

# Future routers will be added here, e.g.:
# from app.api.v1.endpoints.papers import router as papers_router
# router.include_router(papers_router, prefix="/papers")
