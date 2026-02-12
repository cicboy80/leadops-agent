from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import EmailDraft
from app.repositories.base import BaseRepository


class EmailDraftRepository(BaseRepository[EmailDraft]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailDraft)
