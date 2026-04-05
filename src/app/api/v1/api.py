"""API v1 router configuration."""

from fastapi import APIRouter, Depends

from app.api.v1.endpoints import health, mri
from app.core.security import get_current_user

api_router = APIRouter()

# Include health check endpoints (no authentication required)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

# Include MRI processing endpoints (authentication required)
api_router.include_router(
    mri.router,
    prefix="/mri",
    tags=["MRI Processing"],
    dependencies=[Depends(get_current_user)],
)
