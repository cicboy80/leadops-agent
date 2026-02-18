import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging

_no_response_task: asyncio.Task | None = None


async def _no_response_check_loop() -> None:
    """Daily loop that auto-transitions stale EMAIL_SENT leads to NO_RESPONSE."""
    logger = logging.getLogger("leadops.jobs.no_response")
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours
            from app.core.database import async_session_factory
            from app.services.outcome_service import OutcomeService

            async with async_session_factory() as session:
                service = OutcomeService(session)
                results = await service.check_no_response(days=14)
                await session.commit()
                logger.info("NO_RESPONSE check: transitioned %d leads", len(results))
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("NO_RESPONSE check failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()

    # Demo mode: clean up stale sessions and ensure admin/config exist
    if settings.AUTO_SEED_DEMO:
        from app.services.demo_seeder import cleanup_old_sessions, ensure_admin_and_config

        await cleanup_old_sessions()
        await ensure_admin_and_config()

    global _no_response_task
    _no_response_task = asyncio.create_task(_no_response_check_loop())
    yield
    if _no_response_task:
        _no_response_task.cancel()
        try:
            await _no_response_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeadOps Agent",
        description="B2B agentic workflow for lead qualification and follow-up",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1.router import v1_router
    from app.middleware.correlation import CorrelationMiddleware
    from app.middleware.error_handler import error_handler_middleware

    app.add_middleware(CorrelationMiddleware)
    app.middleware("http")(error_handler_middleware)

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
