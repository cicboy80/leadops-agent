"""LangGraph checkpointer setup using shared Postgres connection."""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace(
            "postgresql://", "postgresql://"
        )
        _checkpointer = AsyncPostgresSaver.from_conn_string(sync_url)
        await _checkpointer.setup()
    return _checkpointer
