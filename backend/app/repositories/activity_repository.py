from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ActivityLog
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[ActivityLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ActivityLog)
