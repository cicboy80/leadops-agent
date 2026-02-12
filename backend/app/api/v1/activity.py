"""Activity log endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_lead_service
from app.models.schemas import ActivityListResponse, ActivityResponse
from app.repositories.activity_repository import ActivityRepository
from app.services.lead_service import LeadService

router = APIRouter()


@router.get("/{lead_id}/activity", response_model=ActivityListResponse, tags=["activity"])
async def get_lead_activity(
    lead_id: uuid.UUID,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
) -> ActivityListResponse:
    """Get activity log for a specific lead."""
    activity_repo = ActivityRepository(lead_service.session)
    items, next_cursor = await activity_repo.list(
        filters={"lead_id": lead_id},
        cursor=cursor,
        limit=limit,
    )
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
