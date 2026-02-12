from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ScoringConfig
from app.repositories.base import BaseRepository

DEFAULT_WEIGHTS = {
    "urgency": 0.25,
    "budget": 0.20,
    "company_size": 0.15,
    "pain_point": 0.15,
    "job_title": 0.10,
    "industry": 0.10,
    "source": 0.05,
}

DEFAULT_THRESHOLDS = {
    "hot": 70,
    "warm": 40,
}


class ScoringConfigRepository(BaseRepository[ScoringConfig]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ScoringConfig)

    async def get_active(self) -> ScoringConfig:
        stmt = select(ScoringConfig).order_by(ScoringConfig.updated_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()
        if config is None:
            config = await self.create(
                weights=DEFAULT_WEIGHTS,
                thresholds=DEFAULT_THRESHOLDS,
            )
        return config
