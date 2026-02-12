import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


async def error_handler_middleware(request: Request, call_next):  # noqa: ANN001
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("unhandled_error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                }
            },
        )
