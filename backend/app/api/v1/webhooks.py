"""Webhook endpoints for external integrations."""

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status

from app.api.deps import get_calendar_service, get_current_user
from app.services.calendar_service import CalendarService

router = APIRouter()


@router.post("/calendly", tags=["webhooks"])
async def calendly_webhook(
    request: Request,
    calendar_service: CalendarService = Depends(get_calendar_service),
    calendly_webhook_signature: str | None = Header(default=None),
) -> dict:
    """Receive Calendly invitee.created webhook.

    Verifies signature if CALENDLY_WEBHOOK_SECRET is configured.
    """
    body = await request.body()

    # Verify signature
    if calendly_webhook_signature:
        if not CalendarService.verify_webhook_signature(body, calendly_webhook_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    payload = await request.json()
    event_type = payload.get("event")

    if event_type != "invitee.created":
        return {"status": "ignored", "reason": f"unhandled event: {event_type}"}

    result = await calendar_service.handle_booking_webhook(payload)
    return result
