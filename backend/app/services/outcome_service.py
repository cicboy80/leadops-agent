"""Service for managing lead outcome stage transitions."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityType, OutcomeStage
from app.models.orm import Lead, LeadOutcomeStage
from app.repositories.activity_repository import ActivityRepository
from app.repositories.outcome_stage_repository import (
    VALID_TRANSITIONS,
    OutcomeStageRepository,
)
from app.services.scoring_config_service import ScoringConfigService

logger = structlog.get_logger()

# Terminal stages that trigger learning weight updates
TERMINAL_STAGES = {
    OutcomeStage.CLOSED_WON.value,
    OutcomeStage.CLOSED_LOST.value,
    OutcomeStage.DISQUALIFIED.value,
}

# Map outcome stages to the old OutcomeType values used by scoring
STAGE_TO_OUTCOME = {
    OutcomeStage.BOOKED_DEMO.value: "booked_demo",
    OutcomeStage.CLOSED_WON.value: "closed_won",
    OutcomeStage.CLOSED_LOST.value: "closed_lost",
    OutcomeStage.DISQUALIFIED.value: "disqualified",
    OutcomeStage.NO_RESPONSE.value: "no_response",
}


class OutcomeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stage_repo = OutcomeStageRepository(session)
        self.activity_repo = ActivityRepository(session)

    async def transition_stage(
        self,
        lead_id: uuid.UUID,
        new_stage: OutcomeStage,
        notes: str | None = None,
        triggered_by: str = "user",
    ) -> LeadOutcomeStage:
        """Validate and execute a stage transition."""
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        current = lead.current_outcome_stage
        new_stage_val = new_stage.value

        # Validate transition
        if current is None:
            raise ValueError("Lead has no outcome stage yet. Email must be sent first.")

        valid_next = VALID_TRANSITIONS.get(current, set())
        if new_stage_val not in valid_next:
            raise ValueError(
                f"Invalid transition from {current} to {new_stage_val}. "
                f"Valid transitions: {', '.join(sorted(valid_next)) or 'none (terminal stage)'}"
            )

        logger.info(
            "Transitioning outcome stage",
            lead_id=str(lead_id),
            from_stage=current,
            to_stage=new_stage_val,
        )

        record = await self.stage_repo.transition_to_stage(
            lead_id=lead_id,
            new_stage=new_stage_val,
            reason="MANUAL",
            triggered_by=triggered_by,
            notes=notes,
        )

        # Log activity
        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.STATUS_CHANGED.value,
            payload={
                "outcome_stage_from": current,
                "outcome_stage_to": new_stage_val,
                "triggered_by": triggered_by,
            },
        )

        # Trigger learning update for terminal outcomes
        if new_stage_val in TERMINAL_STAGES and lead.score_value is not None:
            outcome_key = STAGE_TO_OUTCOME.get(new_stage_val)
            if outcome_key:
                scoring_service = ScoringConfigService(self.session)
                await scoring_service.update_weights_from_feedback(
                    outcome=outcome_key,
                    lead_score=lead.score_value,
                )
                logger.info(
                    "Learning weights updated from stage transition",
                    lead_id=str(lead_id),
                    stage=new_stage_val,
                )

        return record

    async def handle_email_sent(self, lead_id: uuid.UUID) -> LeadOutcomeStage:
        """Set the initial EMAIL_SENT stage after an email is approved and sent."""
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        # If already in an outcome stage, don't overwrite
        if lead.current_outcome_stage is not None:
            logger.info(
                "Lead already has outcome stage, skipping EMAIL_SENT",
                lead_id=str(lead_id),
                current_stage=lead.current_outcome_stage,
            )
            # Return the existing current stage record
            history = await self.stage_repo.get_stage_history(lead_id)
            return history[-1] if history else await self.stage_repo.transition_to_stage(
                lead_id=lead_id,
                new_stage=OutcomeStage.EMAIL_SENT.value,
                reason="SYSTEM",
                triggered_by="system",
            )

        record = await self.stage_repo.transition_to_stage(
            lead_id=lead_id,
            new_stage=OutcomeStage.EMAIL_SENT.value,
            reason="SYSTEM",
            triggered_by="system",
        )

        logger.info("EMAIL_SENT stage set", lead_id=str(lead_id))
        return record

    async def handle_inbound_reply(
        self,
        lead_id: uuid.UUID,
        reply_body: str,
        sender_email: str | None = None,
    ) -> dict:
        """Handle an inbound reply with LLM classification and auto-routing.

        Returns a dict with classification details and any stage transition record.
        """
        from app.models.enums import ReplyClassification
        from app.services.calendar_service import CalendarService
        from app.services.notification_service import NotificationService
        from app.services.reply_classification_service import ReplyClassificationService

        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        current = lead.current_outcome_stage
        truncated_body = reply_body[:500]
        lead_name = f"{lead.first_name} {lead.last_name}"

        # 1. Log EMAIL_REPLIED activity
        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.EMAIL_REPLIED.value,
            payload={
                "reply_body": truncated_body,
                "sender_email": sender_email,
            },
        )

        # 2. Classify the reply
        classification_service = ReplyClassificationService(self.session)
        classification_record = await classification_service.classify_reply(
            lead_id=lead_id,
            reply_body=reply_body,
            sender_email=sender_email,
        )

        classification = ReplyClassification(classification_record.classification)
        notification_service = NotificationService(self.session)
        calendar_service = CalendarService(self.session)

        stage_record = None
        auto_action = None

        auto_transition_stages = {
            OutcomeStage.EMAIL_SENT.value,
            OutcomeStage.NO_RESPONSE.value,
        }

        # 3. Route based on classification
        if classification == ReplyClassification.OUT_OF_OFFICE:
            auto_action = "No stage transition (out-of-office detected)"
            await notification_service.notify_reply_classified(
                lead_id=lead_id,
                classification=classification.value,
                reply_preview=truncated_body,
                lead_name=lead_name,
            )

        elif classification == ReplyClassification.UNSUBSCRIBE:
            if current in auto_transition_stages or current == OutcomeStage.RESPONDED.value:
                stage_record = await self.stage_repo.transition_to_stage(
                    lead_id=lead_id,
                    new_stage=OutcomeStage.DISQUALIFIED.value,
                    reason="AUTOMATIC",
                    triggered_by="reply_agent",
                    notes=f"Unsubscribe request: {truncated_body[:100]}",
                )
                auto_action = "Auto-transitioned to Disqualified"
                await self._log_stage_change(lead_id, current, OutcomeStage.DISQUALIFIED.value, "reply_agent")
            await notification_service.notify_reply_classified(
                lead_id=lead_id,
                classification=classification.value,
                reply_preview=truncated_body,
                lead_name=lead_name,
            )

        elif classification == ReplyClassification.NOT_INTERESTED:
            if current in auto_transition_stages or current == OutcomeStage.RESPONDED.value:
                stage_record = await self.stage_repo.transition_to_stage(
                    lead_id=lead_id,
                    new_stage=OutcomeStage.CLOSED_LOST.value,
                    reason="AUTOMATIC",
                    triggered_by="reply_agent",
                    notes=f"Not interested: {truncated_body[:100]}",
                )
                auto_action = "Auto-transitioned to Closed Lost"
                await self._log_stage_change(lead_id, current, OutcomeStage.CLOSED_LOST.value, "reply_agent")
            await notification_service.notify_reply_classified(
                lead_id=lead_id,
                classification=classification.value,
                reply_preview=truncated_body,
                lead_name=lead_name,
            )

        elif classification == ReplyClassification.INTERESTED_BOOK_DEMO:
            # Transition to RESPONDED if needed
            if current in auto_transition_stages:
                stage_record = await self.stage_repo.transition_to_stage(
                    lead_id=lead_id,
                    new_stage=OutcomeStage.RESPONDED.value,
                    reason="AUTOMATIC",
                    triggered_by="reply_agent",
                    notes=f"Interested reply: {truncated_body[:100]}",
                )
                await self._log_stage_change(lead_id, current, OutcomeStage.RESPONDED.value, "reply_agent")

            # Get scheduling link
            scheduling_link = await calendar_service.get_booking_link(lead_id)
            auto_action = f"Transitioned to Responded, scheduling link generated"

            await notification_service.notify_demo_requested(
                lead_id=lead_id,
                scheduling_link=scheduling_link,
                extracted_dates=classification_record.extracted_dates or [],
                lead_name=lead_name,
            )

        elif classification == ReplyClassification.QUESTION:
            if current in auto_transition_stages:
                stage_record = await self.stage_repo.transition_to_stage(
                    lead_id=lead_id,
                    new_stage=OutcomeStage.RESPONDED.value,
                    reason="AUTOMATIC",
                    triggered_by="reply_agent",
                    notes=f"Question reply: {truncated_body[:100]}",
                )
                auto_action = "Transitioned to Responded (question received)"
                await self._log_stage_change(lead_id, current, OutcomeStage.RESPONDED.value, "reply_agent")
            await notification_service.notify_reply_classified(
                lead_id=lead_id,
                classification=classification.value,
                reply_preview=truncated_body,
                lead_name=lead_name,
            )

        else:  # UNCLEAR
            if current in auto_transition_stages:
                stage_record = await self.stage_repo.transition_to_stage(
                    lead_id=lead_id,
                    new_stage=OutcomeStage.RESPONDED.value,
                    reason="AUTOMATIC",
                    triggered_by="reply_agent",
                    notes=f"Unclear reply: {truncated_body[:100]}",
                )
                auto_action = "Transitioned to Responded (needs review)"
                await self._log_stage_change(lead_id, current, OutcomeStage.RESPONDED.value, "reply_agent")
            await notification_service.notify_reply_classified(
                lead_id=lead_id,
                classification=classification.value,
                reply_preview=truncated_body,
                lead_name=lead_name,
            )

        logger.info(
            "Inbound reply processed",
            lead_id=str(lead_id),
            classification=classification.value,
            auto_action=auto_action,
        )

        return {
            "stage_record": stage_record,
            "classification": classification_record.classification,
            "confidence": classification_record.confidence,
            "reasoning": classification_record.reasoning,
            "extracted_dates": classification_record.extracted_dates or [],
            "auto_action_taken": auto_action,
        }

    async def _log_stage_change(
        self,
        lead_id: uuid.UUID,
        from_stage: str | None,
        to_stage: str,
        triggered_by: str,
    ) -> None:
        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.STATUS_CHANGED.value,
            payload={
                "outcome_stage_from": from_stage,
                "outcome_stage_to": to_stage,
                "triggered_by": triggered_by,
            },
        )

    async def check_no_response(self, days: int = 14) -> list[LeadOutcomeStage]:
        """Find stale EMAIL_SENT leads and auto-transition to NO_RESPONSE."""
        stale_leads = await self.stage_repo.get_stale_email_sent(days=days)
        results = []

        for lead in stale_leads:
            try:
                record = await self.stage_repo.transition_to_stage(
                    lead_id=lead.id,
                    new_stage=OutcomeStage.NO_RESPONSE.value,
                    reason="AUTOMATIC",
                    triggered_by="system",
                    notes=f"Auto-transitioned after {days} days with no response",
                )

                await self.activity_repo.create(
                    lead_id=lead.id,
                    type=ActivityType.STATUS_CHANGED.value,
                    payload={
                        "outcome_stage_from": OutcomeStage.EMAIL_SENT.value,
                        "outcome_stage_to": OutcomeStage.NO_RESPONSE.value,
                        "triggered_by": "system",
                        "reason": f"auto_no_response_{days}d",
                    },
                )

                results.append(record)
                logger.info("Auto NO_RESPONSE transition", lead_id=str(lead.id))
            except Exception as e:
                logger.error("Failed auto NO_RESPONSE", lead_id=str(lead.id), error=str(e))

        logger.info("NO_RESPONSE check completed", transitioned=len(results))
        return results

    async def get_history(self, lead_id: uuid.UUID) -> list[LeadOutcomeStage]:
        """Return full stage timeline for a lead."""
        return await self.stage_repo.get_stage_history(lead_id)

    async def get_valid_next_stages(self, lead_id: uuid.UUID) -> tuple[str | None, list[str]]:
        """Return current stage and valid next stages."""
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        current = lead.current_outcome_stage
        if current is None:
            return None, []

        valid_next = VALID_TRANSITIONS.get(current, set())
        return current, sorted(valid_next)
