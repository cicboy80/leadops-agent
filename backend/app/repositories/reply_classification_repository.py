"""Repository for reply classification records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ReplyClassificationRecord
from app.repositories.base import BaseRepository


class ReplyClassificationRepository(BaseRepository[ReplyClassificationRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReplyClassificationRecord)

    async def get_latest_for_lead(self, lead_id: uuid.UUID) -> ReplyClassificationRecord | None:
        stmt = (
            select(ReplyClassificationRecord)
            .where(ReplyClassificationRecord.lead_id == lead_id)
            .order_by(ReplyClassificationRecord.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_for_lead(self, lead_id: uuid.UUID) -> list[ReplyClassificationRecord]:
        stmt = (
            select(ReplyClassificationRecord)
            .where(ReplyClassificationRecord.lead_id == lead_id)
            .order_by(ReplyClassificationRecord.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def override(
        self,
        classification_id: uuid.UUID,
        new_classification: str,
        overridden_by: str,
    ) -> ReplyClassificationRecord:
        record = await self.get_by_id(classification_id)
        if record is None:
            raise ValueError(f"Classification {classification_id} not found")

        record.overridden_by = overridden_by
        record.overridden_classification = new_classification
        record.overridden_at = datetime.now(timezone.utc)
        await self.session.flush()
        return record
