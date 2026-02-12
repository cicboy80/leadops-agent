"""Server-Sent Events (SSE) streaming endpoint for pipeline processing updates."""

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_pipeline_service

router = APIRouter()


async def event_generator(lead_id: str | None, pipeline_service) -> str:
    """Generate SSE events for pipeline processing updates.

    Event format:
        data: {"lead_id": "uuid", "node": "score", "status": "completed", "timestamp": "..."}

    Args:
        lead_id: Optional filter for a specific lead
        pipeline_service: Pipeline service instance

    Yields:
        SSE-formatted event strings
    """
    # TODO Phase 2: Implement real-time event streaming
    # This should connect to a message queue or event bus that receives
    # updates from the LangGraph execution layer.
    #
    # For now, send a placeholder event and close
    await asyncio.sleep(0.1)

    event = {
        "type": "info",
        "message": "Event streaming not yet implemented",
        "lead_id": lead_id,
    }

    yield f"data: {json.dumps(event)}\n\n"


@router.get("/processing-stream", tags=["stream"])
async def processing_stream(
    lead_id: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
    pipeline_service: None = Depends(get_pipeline_service),
) -> StreamingResponse:
    """Server-Sent Events stream for real-time pipeline processing updates.

    Query parameters:
    - lead_id: Optional filter to only receive events for a specific lead

    Event types:
    - pipeline_started: Pipeline execution begins
    - node_started: Graph node begins execution
    - node_completed: Graph node completes successfully
    - node_failed: Graph node encounters an error
    - pipeline_completed: Pipeline execution finishes
    - pipeline_failed: Pipeline execution fails

    Keep connection open to receive events as they occur.
    """
    return StreamingResponse(
        event_generator(lead_id, pipeline_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        },
    )
