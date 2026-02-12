from fastapi import APIRouter

from app.api.v1 import activity, dashboard, drafts, health, leads, notifications, settings, stream, traces, webhooks

v1_router = APIRouter()

v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(leads.router, prefix="/leads", tags=["leads"])
v1_router.include_router(drafts.router, prefix="/leads", tags=["drafts"])
v1_router.include_router(activity.router, prefix="/leads", tags=["activity"])
v1_router.include_router(traces.router, prefix="/leads", tags=["traces"])
v1_router.include_router(settings.router, prefix="/settings", tags=["settings"])
v1_router.include_router(stream.router, prefix="/leads", tags=["stream"])
v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
v1_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
