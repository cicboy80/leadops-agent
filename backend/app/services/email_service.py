import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ActivityType, DeliveryStatus, EmailVariant, LeadStatus
from app.models.orm import EmailDraft
from app.repositories.activity_repository import ActivityRepository
from app.repositories.email_draft_repository import EmailDraftRepository
from app.repositories.lead_repository import LeadRepository

logger = structlog.get_logger()


class EmailService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_draft_repo = EmailDraftRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.lead_repo = LeadRepository(session)

    async def get_drafts(
        self,
        lead_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[EmailDraft], str | None]:
        """
        Get email drafts for a lead with pagination.
        """
        return await self.email_draft_repo.list(
            filters={"lead_id": lead_id},
            cursor=cursor,
            limit=limit,
        )

    async def create_draft(
        self,
        lead_id: uuid.UUID,
        subject: str,
        body: str,
        variant: str = "first_touch",
    ) -> EmailDraft:
        """
        Create an email draft and log EMAIL_DRAFTED activity.

        Args:
            lead_id: UUID of the lead
            subject: Email subject line
            body: Email body content
            variant: Email variant type (default: first_touch)

        Returns:
            Created EmailDraft
        """
        logger.info("Creating email draft", lead_id=str(lead_id), subject=subject, variant=variant)

        # Validate variant
        try:
            EmailVariant(variant)
        except ValueError:
            logger.warning("Invalid email variant, using default", variant=variant)
            variant = EmailVariant.FIRST_TOUCH.value

        draft = await self.email_draft_repo.create(
            lead_id=lead_id,
            subject=subject,
            body=body,
            variant=variant,
            approved=False,
            delivery_status=DeliveryStatus.PENDING.value,
        )

        # Log EMAIL_DRAFTED activity
        await self.activity_repo.create(
            lead_id=lead_id,
            type=ActivityType.EMAIL_DRAFTED.value,
            payload={
                "draft_id": str(draft.id),
                "subject": subject,
                "variant": variant,
            },
        )

        logger.info("Email draft created", draft_id=str(draft.id))

        return draft

    async def approve_and_send(self, draft_id: uuid.UUID) -> EmailDraft:
        """
        Approve an email draft and send it based on EMAIL_MODE configuration.

        In mock mode: sets delivery_status=SENT and sent_at=now
        In other modes: placeholder for real sending logic

        Args:
            draft_id: UUID of the draft to approve and send

        Returns:
            Updated EmailDraft with delivery status
        """
        draft = await self.email_draft_repo.get_by_id(draft_id)
        if draft is None:
            raise ValueError(f"Email draft {draft_id} not found")

        logger.info("Approving and sending email draft", draft_id=str(draft_id), mode=settings.EMAIL_MODE)

        # Set approved flag
        draft = await self.email_draft_repo.update(
            draft,
            approved=True,
        )

        # Handle sending based on EMAIL_MODE
        if settings.EMAIL_MODE == "mock":
            # Mock mode - simulate successful send
            draft = await self.email_draft_repo.update(
                draft,
                delivery_status=DeliveryStatus.SENT.value,
                sent_at=datetime.utcnow(),
            )

            logger.info("Email sent (mock mode)", draft_id=str(draft_id))

            # Log EMAIL_SENT activity
            await self.activity_repo.create(
                lead_id=draft.lead_id,
                type=ActivityType.EMAIL_SENT.value,
                payload={
                    "draft_id": str(draft.id),
                    "subject": draft.subject,
                    "mode": "mock",
                },
            )

            # Update lead status to CONTACTED
            lead = await self.lead_repo.get_by_id(draft.lead_id)
            if lead is not None:
                await self.lead_repo.update(lead, status=LeadStatus.CONTACTED.value)
                logger.info("Lead status updated to CONTACTED", lead_id=str(draft.lead_id))

        elif settings.EMAIL_MODE == "smtp":
            # Placeholder for SMTP sending
            logger.warning("SMTP mode not yet implemented", draft_id=str(draft_id))
            draft = await self.email_draft_repo.update(
                draft,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message="SMTP sending not implemented",
            )

        elif settings.EMAIL_MODE == "sendgrid":
            # Placeholder for SendGrid API
            logger.warning("SendGrid mode not yet implemented", draft_id=str(draft_id))
            draft = await self.email_draft_repo.update(
                draft,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message="SendGrid sending not implemented",
            )

        else:
            logger.error("Unknown EMAIL_MODE", mode=settings.EMAIL_MODE)
            draft = await self.email_draft_repo.update(
                draft,
                delivery_status=DeliveryStatus.FAILED.value,
                error_message=f"Unknown email mode: {settings.EMAIL_MODE}",
            )

        return draft
