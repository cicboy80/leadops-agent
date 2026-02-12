"""Trace log endpoints for pipeline execution observability."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_trace_service
from app.models.schemas import TraceListResponse, TraceResponse
from app.services.trace_service import TraceService

router = APIRouter()


@router.get("/{lead_id}/traces", response_model=TraceListResponse, tags=["traces"])
async def get_lead_traces(
    lead_id: uuid.UUID,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    user: str = Depends(get_current_user),
    trace_service: TraceService = Depends(get_trace_service),
) -> TraceListResponse:
    """Get execution traces for a specific lead."""
    items, next_cursor = await trace_service.get_traces(lead_id, cursor=cursor, limit=limit)
    return TraceListResponse(
        items=[TraceResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
