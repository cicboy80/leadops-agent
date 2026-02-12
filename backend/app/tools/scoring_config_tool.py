"""Scoring config tool — read/write scoring weights from database."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.scoring_config_repository import ScoringConfigRepository


class ScoringConfigTool:
    def __init__(self, session: AsyncSession):
        self.repo = ScoringConfigRepository(session)

    async def get_weights(self) -> dict:
        config = await self.repo.get_active()
        return config.weights

    async def get_thresholds(self) -> dict:
        config = await self.repo.get_active()
        return config.thresholds

    async def get_config(self) -> dict:
        config = await self.repo.get_active()
        return {"weights": config.weights, "thresholds": config.thresholds}
