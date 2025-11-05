"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies all dependencies are ready
    """
    checks = {
        "database": False,
        # "redis": False,
        # "rabbitmq": False,
        # "minio": False,
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        checks["database"] = result.scalar() == 1
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        checks["database"] = False

    # TODO: Check Redis connection
    # TODO: Check RabbitMQ connection
    # TODO: Check MinIO connection

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies service is alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
