"""Dashboard stats endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
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


@router.get("/stats", response_model=DashboardStatsResponse, tags=["dashboard"])
async def get_dashboard_stats(
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsResponse:
    """Get aggregate dashboard statistics."""
    total = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
    hot = (await db.execute(select(func.count(Lead.id)).where(Lead.score_label == "HOT", Lead.status == "NEW"))).scalar() or 0
    warm = (await db.execute(select(func.count(Lead.id)).where(Lead.score_label == "WARM", Lead.status == "NEW"))).scalar() or 0
    cold = (await db.execute(select(func.count(Lead.id)).where(Lead.score_label == "COLD", Lead.status == "NEW"))).scalar() or 0

    # Stage-based counts — cumulative so leads don't "fall out" as they progress.
    # Pipeline: EMAIL_SENT → RESPONDED → BOOKED_DEMO → CLOSED_WON/CLOSED_LOST
    # A lead at CLOSED_WON has been contacted, has responded, AND has booked a demo.
    all_stages = ["EMAIL_SENT", "RESPONDED", "NO_RESPONSE", "BOOKED_DEMO",
                  "CLOSED_WON", "CLOSED_LOST", "DISQUALIFIED"]
    contacted = (await db.execute(select(func.count(Lead.id)).where(
        Lead.current_outcome_stage.in_(all_stages)
    ))).scalar() or 0
    meetings = (await db.execute(select(func.count(Lead.id)).where(
        Lead.current_outcome_stage.in_(["BOOKED_DEMO", "CLOSED_WON"])
    ))).scalar() or 0
    responded = (await db.execute(select(func.count(Lead.id)).where(
        Lead.current_outcome_stage.in_(["RESPONDED", "BOOKED_DEMO", "CLOSED_WON", "CLOSED_LOST"])
    ))).scalar() or 0
    closed_won = (await db.execute(select(func.count(Lead.id)).where(
        Lead.current_outcome_stage == "CLOSED_WON"
    ))).scalar() or 0
    closed_lost = (await db.execute(select(func.count(Lead.id)).where(
        Lead.current_outcome_stage == "CLOSED_LOST"
    ))).scalar() or 0

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
