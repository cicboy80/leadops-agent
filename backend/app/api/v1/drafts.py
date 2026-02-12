"""Email draft management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_draft_service, get_outcome_service
from app.models.schemas import (
    EmailDraftCreate,
    EmailDraftListResponse,
    EmailDraftResponse,
)
from app.services.email_service import EmailService
from app.services.outcome_service import OutcomeService

router = APIRouter()


@router.get("/{lead_id}/drafts", response_model=EmailDraftListResponse, tags=["drafts"])
async def list_drafts(
    lead_id: uuid.UUID,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    user: str = Depends(get_current_user),
    draft_service: EmailService = Depends(get_draft_service),
) -> EmailDraftListResponse:
    """List all email drafts for a specific lead."""
    items, next_cursor = await draft_service.get_drafts(lead_id, cursor=cursor, limit=limit)
    return EmailDraftListResponse(
        items=[EmailDraftResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.post("/{lead_id}/drafts", response_model=EmailDraftResponse, status_code=status.HTTP_201_CREATED, tags=["drafts"])
async def create_draft(
    lead_id: uuid.UUID,
    draft: EmailDraftCreate,
    user: str = Depends(get_current_user),
    draft_service: EmailService = Depends(get_draft_service),
) -> EmailDraftResponse:
    """Manually create an email draft for a lead."""
    result = await draft_service.create_draft(
        lead_id=lead_id,
        subject=draft.subject,
        body=draft.body,
        variant=draft.variant.value if hasattr(draft.variant, 'value') else draft.variant,
    )
    return EmailDraftResponse.model_validate(result)


@router.post(
    "/{lead_id}/drafts/{draft_id}/approve_send",
    response_model=EmailDraftResponse,
    tags=["drafts"],
)
async def approve_and_send_draft(
    lead_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: str = Depends(get_current_user),
    draft_service: EmailService = Depends(get_draft_service),
    outcome_service: OutcomeService = Depends(get_outcome_service),
) -> EmailDraftResponse:
    """Approve and send an email draft."""
    try:
        result = await draft_service.approve_and_send(draft_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Set initial EMAIL_SENT outcome stage
    if result.delivery_status == "SENT":
        try:
            await outcome_service.handle_email_sent(lead_id)
        except Exception:
            pass  # Don't fail the approve if stage tracking fails

    return EmailDraftResponse.model_validate(result)
