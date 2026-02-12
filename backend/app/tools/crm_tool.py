"""CRM tool — database operations for activity logging."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ActivityLog


class CRMTool:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_activity(
        self,
        lead_id: uuid.UUID,
        activity_type: str,
        payload: dict[str, Any] | None = None,
    ) -> ActivityLog:
        activity = ActivityLog(
            lead_id=lead_id,
            type=activity_type,
            payload=payload,
        )
        self.session.add(activity)
        await self.session.flush()
        return activity
