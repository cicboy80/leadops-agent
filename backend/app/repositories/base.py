import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model_class: type[ModelT]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model_class, id)

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 50,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> tuple[list[ModelT], str | None]:
        stmt = select(self.model_class)

        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model_class, key):
                    if isinstance(value, list):
                        stmt = stmt.where(getattr(self.model_class, key).in_(value))
                    else:
                        stmt = stmt.where(getattr(self.model_class, key) == value)

        col = getattr(self.model_class, order_by)
        if cursor:
            cursor_val = cursor
            if descending:
                stmt = stmt.where(col < cursor_val)
            else:
                stmt = stmt.where(col > cursor_val)

        stmt = stmt.order_by(col.desc() if descending else col.asc())
        stmt = stmt.limit(limit + 1)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = str(getattr(last, order_by))

        return items, next_cursor

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self.model_class)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()
