"""Dependency injection functions for API routes."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.calendar_service import CalendarService
from app.services.email_service import EmailService
from app.services.lead_service import LeadService
from app.services.notification_service import NotificationService
from app.services.outcome_service import OutcomeService
from app.services.pipeline_service import PipelineService
from app.services.reply_classification_service import ReplyClassificationService
from app.services.scoring_config_service import ScoringConfigService
from app.services.trace_service import TraceService

# Re-export core dependencies
__all__ = [
    "get_db",
    "get_current_user",
    "get_lead_service",
    "get_pipeline_service",
    "get_draft_service",
    "get_trace_service",
    "get_scoring_config_service",
    "get_outcome_service",
    "get_reply_classification_service",
    "get_notification_service",
    "get_calendar_service",
]


def get_lead_service(db: AsyncSession = Depends(get_db)) -> LeadService:
    return LeadService(db)


def get_pipeline_service(db: AsyncSession = Depends(get_db)) -> PipelineService:
    return PipelineService(db)


def get_draft_service(db: AsyncSession = Depends(get_db)) -> EmailService:
    return EmailService(db)


def get_trace_service(db: AsyncSession = Depends(get_db)) -> TraceService:
    return TraceService(db)


def get_scoring_config_service(db: AsyncSession = Depends(get_db)) -> ScoringConfigService:
    return ScoringConfigService(db)


def get_outcome_service(db: AsyncSession = Depends(get_db)) -> OutcomeService:
    return OutcomeService(db)


def get_reply_classification_service(db: AsyncSession = Depends(get_db)) -> ReplyClassificationService:
    return ReplyClassificationService(db)


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


def get_calendar_service(db: AsyncSession = Depends(get_db)) -> CalendarService:
    return CalendarService(db)
