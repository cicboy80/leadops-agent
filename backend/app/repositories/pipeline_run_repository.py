from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import PipelineRun
from app.repositories.base import BaseRepository


class PipelineRunRepository(BaseRepository[PipelineRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PipelineRun)
