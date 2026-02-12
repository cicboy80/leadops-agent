from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Trace
from app.repositories.base import BaseRepository


class TraceRepository(BaseRepository[Trace]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Trace)
