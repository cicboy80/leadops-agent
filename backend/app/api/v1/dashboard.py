"""Dashboard stats endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_demo_leads, get_current_user, get_db
from app.models.orm import Lead

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    contacted: int
    meetings_booked: int
    responded: int
    closed_won: int
    closed_lost: int


def _session_filter(stmt, demo_session_id: str | None):
    """Add demo_session_id filter to a query when in demo mode."""
    if demo_session_id:
        return stmt.where(Lead.demo_session_id == demo_session_id)
    return stmt


@router.get("/stats", response_model=DashboardStatsResponse, tags=["dashboard"])
async def get_dashboard_stats(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> DashboardStatsResponse:
    """Get aggregate dashboard statistics."""
    base = select(func.count(Lead.id))

    total = (await db.execute(_session_filter(base, demo_session_id))).scalar() or 0
    hot = (await db.execute(_session_filter(base.where(Lead.score_label == "HOT", Lead.status == "NEW"), demo_session_id))).scalar() or 0
    warm = (await db.execute(_session_filter(base.where(Lead.score_label == "WARM", Lead.status == "NEW"), demo_session_id))).scalar() or 0
    cold = (await db.execute(_session_filter(base.where(Lead.score_label == "COLD", Lead.status == "NEW"), demo_session_id))).scalar() or 0

    # Stage-based counts — cumulative so leads don't "fall out" as they progress.
    all_stages = ["EMAIL_SENT", "RESPONDED", "NO_RESPONSE", "BOOKED_DEMO",
                  "CLOSED_WON", "CLOSED_LOST", "DISQUALIFIED"]
    contacted = (await db.execute(_session_filter(base.where(
        Lead.current_outcome_stage.in_(all_stages)
    ), demo_session_id))).scalar() or 0
    meetings = (await db.execute(_session_filter(base.where(
        Lead.current_outcome_stage.in_(["BOOKED_DEMO", "CLOSED_WON"])
    ), demo_session_id))).scalar() or 0
    responded = (await db.execute(_session_filter(base.where(
        Lead.current_outcome_stage.in_(["RESPONDED", "BOOKED_DEMO", "CLOSED_WON", "CLOSED_LOST"])
    ), demo_session_id))).scalar() or 0
    closed_won = (await db.execute(_session_filter(base.where(
        Lead.current_outcome_stage == "CLOSED_WON"
    ), demo_session_id))).scalar() or 0
    closed_lost = (await db.execute(_session_filter(base.where(
        Lead.current_outcome_stage == "CLOSED_LOST"
    ), demo_session_id))).scalar() or 0

    return DashboardStatsResponse(
        total_leads=total,
        hot_leads=hot,
        warm_leads=warm,
        cold_leads=cold,
        contacted=contacted,
        meetings_booked=meetings,
        responded=responded,
        closed_won=closed_won,
        closed_lost=closed_lost,
    )
