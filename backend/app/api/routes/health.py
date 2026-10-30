from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
def check_api_health() -> Dict[str, str]:
    """Basic API health check returning service status and runtime environment."""
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
    }


@router.get("/db")
def check_database_health(db: Session = Depends(get_db)) -> Any:
    """Database connectivity check executing SELECT 1 via an active SQLAlchemy session.

    Returns 200 with status ok if connected, or 503 Service Unavailable if unreachable.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
        }
    except (SQLAlchemyError, Exception) as exc:
        logger.error(f"Database health check failed: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Database is unreachable or connection failed",
                "code": "DATABASE_UNAVAILABLE",
            },
        )
