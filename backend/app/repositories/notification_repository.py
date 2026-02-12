"""Repository for notifications."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def get_unread(self) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.read_at.is_(None))
            .order_by(Notification.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: uuid.UUID) -> Notification:
        record = await self.get_by_id(notification_id)
        if record is None:
            raise ValueError(f"Notification {notification_id} not found")
        record.read_at = datetime.now(timezone.utc)
        await self.session.flush()
        return record

    async def mark_all_read(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.read_at.is_(None))
            .values(read_at=now)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
