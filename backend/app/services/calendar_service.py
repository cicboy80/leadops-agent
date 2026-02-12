"""Calendar integration service with Calendly provider + mock fallback."""

import abc
import hashlib
import hmac
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ActivityType, OutcomeStage
from app.models.orm import Lead
from app.repositories.activity_repository import ActivityRepository
from app.repositories.outcome_stage_repository import OutcomeStageRepository

logger = structlog.get_logger()


class CalendarProvider(abc.ABC):
    @abc.abstractmethod
    async def get_scheduling_link(self, event_type: str | None = None) -> str:
        ...

    @abc.abstractmethod
    async def check_availability(self, date_range: dict) -> list[dict]:
        ...

    @abc.abstractmethod
    async def get_event(self, event_id: str) -> dict | None:
        ...


class CalendlyProvider(CalendarProvider):
    def __init__(self, api_key: str, user_uri: str):
        self.api_key = api_key
        self.user_uri = user_uri

    async def get_scheduling_link(self, event_type: str | None = None) -> str:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.calendly.com/scheduling_links",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params={
                        "owner": self.user_uri,
                        "max_event_count": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("resource", {}).get("booking_url"):
                    return data["resource"]["booking_url"]
        except Exception as e:
            logger.warning("Calendly API call failed", error=str(e))

        # Fallback to constructing a link from user URI
        slug = self.user_uri.rsplit("/", 1)[-1] if self.user_uri else "user"
        return f"https://calendly.com/{slug}"

    async def check_availability(self, date_range: dict) -> list[dict]:
        # Calendly doesn't have a direct availability API for external use
        return []

    async def get_event(self, event_id: str) -> dict | None:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.calendly.com/scheduled_events/{event_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                return resp.json().get("resource")
        except Exception as e:
            logger.warning("Failed to fetch Calendly event", error=str(e))
            return None


class MockCalendarProvider(CalendarProvider):
    async def get_scheduling_link(self, event_type: str | None = None) -> str:
        return "https://calendly.com/mock-user/30min"

    async def check_availability(self, date_range: dict) -> list[dict]:
        return [
            {"date": "2026-02-15", "slots": ["10:00", "14:00", "16:00"]},
            {"date": "2026-02-16", "slots": ["09:00", "11:00", "15:00"]},
        ]

    async def get_event(self, event_id: str) -> dict | None:
        return {"id": event_id, "status": "active", "event_type": "30min"}


def _get_provider() -> CalendarProvider:
    if settings.CALENDLY_API_KEY:
        return CalendlyProvider(
            api_key=settings.CALENDLY_API_KEY,
            user_uri=settings.CALENDLY_USER_URI,
        )
    return MockCalendarProvider()


class CalendarService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = _get_provider()
        self.activity_repo = ActivityRepository(session)
        self.stage_repo = OutcomeStageRepository(session)

    async def get_booking_link(self, lead_id: uuid.UUID) -> str:
        link = await self.provider.get_scheduling_link()

        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.CALENDLY_LINK_SENT.value,
            payload={"scheduling_link": link},
        )

        logger.info("Scheduling link generated", lead_id=str(lead_id), link=link)
        return link

    async def handle_booking_webhook(self, payload: dict) -> dict:
        """Process a Calendly invitee.created webhook."""
        invitee = payload.get("payload", {})
        email = invitee.get("email", "").lower()
        event_uri = invitee.get("event", "")

        if not email:
            logger.warning("Webhook missing invitee email")
            return {"status": "ignored", "reason": "no email"}

        # Look up lead by email
        from sqlalchemy import select

        stmt = select(Lead).where(Lead.email == email).limit(1)
        result = await self.session.execute(stmt)
        lead = result.scalars().first()

        if not lead:
            logger.info("Webhook email not matched to lead", email=email)
            return {"status": "ignored", "reason": "no matching lead"}

        # Transition to BOOKED_DEMO
        current = lead.current_outcome_stage
        if current in {OutcomeStage.RESPONDED.value, OutcomeStage.EMAIL_SENT.value}:
            # If EMAIL_SENT, transition through RESPONDED first
            if current == OutcomeStage.EMAIL_SENT.value:
                await self.stage_repo.transition_to_stage(
                    lead_id=lead.id,
                    new_stage=OutcomeStage.RESPONDED.value,
                    reason="AUTOMATIC",
                    triggered_by="calendly_webhook",
                    notes="Auto-transitioned on demo booking",
                )

            await self.stage_repo.transition_to_stage(
                lead_id=lead.id,
                new_stage=OutcomeStage.BOOKED_DEMO.value,
                reason="AUTOMATIC",
                triggered_by="calendly_webhook",
                notes=f"Demo booked via Calendly. Event: {event_uri}",
            )

            await self.activity_repo.create(
                lead_id=lead.id,
                type=ActivityType.DEMO_BOOKED.value,
                payload={
                    "event_uri": event_uri,
                    "invitee_email": email,
                    "source": "calendly",
                },
            )

            logger.info("Demo booked via webhook", lead_id=str(lead.id))
            return {"status": "booked", "lead_id": str(lead.id)}

        logger.info(
            "Lead not in bookable stage",
            lead_id=str(lead.id),
            current_stage=current,
        )
        return {"status": "ignored", "reason": f"lead in stage {current}"}

    @staticmethod
    def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
        if not settings.CALENDLY_WEBHOOK_SECRET:
            return True  # No secret configured, skip verification
        expected = hmac.new(
            settings.CALENDLY_WEBHOOK_SECRET.encode(),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
