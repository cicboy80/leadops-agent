"""Repository for lead outcome stage transitions."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OutcomeStage
from app.models.orm import Lead, LeadOutcomeStage
from app.repositories.base import BaseRepository

# Valid transitions from each stage
VALID_TRANSITIONS: dict[str, set[str]] = {
    OutcomeStage.EMAIL_SENT.value: {
        OutcomeStage.RESPONDED.value,
        OutcomeStage.NO_RESPONSE.value,
        OutcomeStage.DISQUALIFIED.value,
        OutcomeStage.CLOSED_LOST.value,
    },
    OutcomeStage.RESPONDED.value: {
        OutcomeStage.BOOKED_DEMO.value,
        OutcomeStage.CLOSED_LOST.value,
        OutcomeStage.DISQUALIFIED.value,
    },
    OutcomeStage.BOOKED_DEMO.value: {
        OutcomeStage.CLOSED_WON.value,
        OutcomeStage.CLOSED_LOST.value,
    },
    OutcomeStage.NO_RESPONSE.value: {
        OutcomeStage.RESPONDED.value,
    },
    OutcomeStage.CLOSED_WON.value: set(),  # terminal
    OutcomeStage.CLOSED_LOST.value: {
        OutcomeStage.RESPONDED.value,  # re-engagement
    },
    OutcomeStage.DISQUALIFIED.value: {
        OutcomeStage.RESPONDED.value,  # re-engagement
    },
}


class OutcomeStageRepository(BaseRepository[LeadOutcomeStage]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LeadOutcomeStage)

    async def transition_to_stage(
        self,
        lead_id: uuid.UUID,
        new_stage: str,
        reason: str,
        triggered_by: str | None = None,
        notes: str | None = None,
        metadata: dict | None = None,
    ) -> LeadOutcomeStage:
        """Close the current stage record, create a new one, and update the Lead."""
        now = datetime.now(timezone.utc)

        # Get the lead
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        previous_stage = lead.current_outcome_stage

        # Close existing stage record (set exited_at)
        if previous_stage:
            stmt = select(LeadOutcomeStage).where(
                and_(
                    LeadOutcomeStage.lead_id == lead_id,
                    LeadOutcomeStage.stage == previous_stage,
                    LeadOutcomeStage.exited_at.is_(None),
                )
            )
            result = await self.session.execute(stmt)
            current_record = result.scalars().first()
            if current_record:
                current_record.exited_at = now

        # Create new stage record
        new_record = LeadOutcomeStage(
            lead_id=lead_id,
            stage=new_stage,
            previous_stage=previous_stage,
            reason=reason,
            triggered_by=triggered_by,
            notes=notes,
            metadata_json=metadata,
            entered_at=now,
        )
        self.session.add(new_record)

        # Update denormalized fields on Lead
        lead.current_outcome_stage = new_stage
        lead.outcome_stage_entered_at = now

        await self.session.flush()
        return new_record

    async def get_stage_history(self, lead_id: uuid.UUID) -> list[LeadOutcomeStage]:
        """Get ordered list of all stage transitions for a lead."""
        stmt = (
            select(LeadOutcomeStage)
            .where(LeadOutcomeStage.lead_id == lead_id)
            .order_by(LeadOutcomeStage.entered_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stale_email_sent(self, days: int = 14) -> list[Lead]:
        """Find leads stuck in EMAIL_SENT stage for more than N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(Lead)
            .where(
                and_(
                    Lead.current_outcome_stage == OutcomeStage.EMAIL_SENT.value,
                    Lead.outcome_stage_entered_at <= cutoff,
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
