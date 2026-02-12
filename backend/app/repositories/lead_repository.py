from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Lead)
