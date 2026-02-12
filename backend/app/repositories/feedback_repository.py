from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Feedback)
