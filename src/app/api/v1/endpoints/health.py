"""Health check endpoint."""

import time
from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.models.schemas import HealthCheckResponse
from app.services.fastsurfer import fastsurfer_service

router = APIRouter()


@router.get(
    "",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
)
async def health_check() -> HealthCheckResponse:
    """
    Perform a comprehensive health check of the API.
    
    Returns:
        Health status including API version and dependency statuses
    """
    services = {}
    overall_status = "healthy"
    
    # Check Redis
    start_time = time.time()
    redis_health = redis_client.health_check()
    redis_latency = (time.time() - start_time) * 1000
    
    services["redis"] = {
        "status": redis_health.get("status", "unknown"),
        "latency_ms": round(redis_latency, 2),
        **{k: v for k, v in redis_health.items() if k != "status"},
    }
    
    if redis_health.get("status") != "healthy":
        overall_status = "degraded"
    
    # Check FastSurfer
    start_time = time.time()
    fastsurfer_health = fastsurfer_service.health_check()
    fastsurfer_latency = (time.time() - start_time) * 1000
    
    services["fastsurfer"] = {
        "status": fastsurfer_health.get("status", "unknown"),
        "latency_ms": round(fastsurfer_latency, 2),
        **{k: v for k, v in fastsurfer_health.items() if k != "status"},
    }
    
    if fastsurfer_health.get("status") == "unhealthy":
        overall_status = "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get(
    "/live",
    summary="Liveness Check",
    description="Simple liveness probe for container orchestration",
)
async def liveness() -> dict:
    """
    Simple liveness check.
    
    Returns:
        Simple OK status indicating the API is running
    """
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Readiness probe to check if the API is ready to serve requests",
)
async def readiness() -> JSONResponse:
    """
    Readiness check for the API.
    
    Verifies that critical dependencies (Redis) are available.
    
    Returns:
        OK status if ready, 503 if not ready
    """
    # Check Redis connection
    if not redis_client.is_connected():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "Redis not connected"},
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready"},
    )
