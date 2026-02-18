"""Notification API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import ensure_demo_leads, get_current_user, get_notification_service
from app.models.schemas import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse, tags=["notifications"])
async def list_notifications(
    unread_only: bool = Query(default=False),
    user: str = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> NotificationListResponse:
    """List notifications, optionally filtered to unread only."""
    items = await notification_service.get_all(
        unread_only=unread_only,
        demo_session_id=demo_session_id,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse, tags=["notifications"])
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: str = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> NotificationResponse:
    """Mark a single notification as read."""
    try:
        record = await notification_service.mark_read(notification_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return NotificationResponse.model_validate(record)


@router.post("/read-all", tags=["notifications"])
async def mark_all_notifications_read(
    user: str = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> dict:
    """Mark all unread notifications as read."""
    count = await notification_service.mark_all_read(demo_session_id=demo_session_id)
    return {"marked_read": count}
