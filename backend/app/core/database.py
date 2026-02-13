import ssl as _ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings

_db_url = settings.DATABASE_URL
_is_sqlite = _db_url.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.ENVIRONMENT == "development",
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    # asyncpg doesn't understand sslmode=require; strip it and pass ssl context
    if "sslmode=require" in _db_url:
        _db_url = _db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        try:
            import certifi
            _ssl_ctx = _ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            _ssl_ctx = _ssl.create_default_context()
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = _ssl.CERT_NONE
        _engine_kwargs["connect_args"] = {"ssl": _ssl_ctx}

engine = create_async_engine(_db_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
