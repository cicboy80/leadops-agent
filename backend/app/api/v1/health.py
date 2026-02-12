"""Health check endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return health status of the application and its dependencies.

    Checks:
    - Database connectivity
    - LLM provider configuration
    - Overall service status
    """
    db_status = "healthy"
    llm_status = "configured" if settings.LLM_PROVIDER else "not_configured"

    # Test database connection
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )

    return HealthResponse(
        status="healthy",
        database=db_status,
        llm=llm_status,
        version="0.1.0",
    )
