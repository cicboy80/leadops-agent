"""Service for in-app notifications."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Notification
from app.repositories.notification_repository import NotificationRepository

logger = structlog.get_logger()


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    async def notify_reply_classified(
        self,
        lead_id: uuid.UUID,
        classification: str,
        reply_preview: str,
        lead_name: str = "",
    ) -> Notification:
        title = f"Reply classified: {classification}"
        body = f"Lead {lead_name} replied. Classification: {classification}. Preview: {reply_preview[:200]}"

        return await self.repo.create(
            lead_id=lead_id,
            type="reply_classified",
            title=title,
            body=body,
            metadata_json={"classification": classification},
        )

    async def notify_demo_requested(
        self,
        lead_id: uuid.UUID,
        scheduling_link: str | None,
        extracted_dates: list[str],
        lead_name: str = "",
    ) -> Notification:
        title = f"Demo requested by {lead_name}" if lead_name else "Demo requested"
        body_parts = [f"Lead {lead_name} wants to book a demo."]
        if extracted_dates:
            body_parts.append(f"Suggested dates: {', '.join(extracted_dates)}")
        if scheduling_link:
            body_parts.append(f"Scheduling link: {scheduling_link}")

        return await self.repo.create(
            lead_id=lead_id,
            type="demo_requested",
            title=title,
            body=" ".join(body_parts),
            metadata_json={
                "scheduling_link": scheduling_link,
                "extracted_dates": extracted_dates,
                "priority": "high",
            },
        )

    async def get_unread(self) -> list[Notification]:
        return await self.repo.get_unread()

    async def get_all(self, unread_only: bool = False) -> list[Notification]:
        if unread_only:
            return await self.repo.get_unread()
        items, _ = await self.repo.list(limit=100)
        return items

    async def mark_read(self, notification_id: uuid.UUID) -> Notification:
        return await self.repo.mark_read(notification_id)

    async def mark_all_read(self) -> int:
        return await self.repo.mark_all_read()
