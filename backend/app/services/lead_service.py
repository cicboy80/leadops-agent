import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityType, LeadStatus
from app.models.orm import Lead
from app.models.schemas import CSVUploadResponse, LeadCreate
from app.repositories.activity_repository import ActivityRepository
from app.repositories.lead_repository import LeadRepository

logger = structlog.get_logger()


class LeadService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.activity_repo = ActivityRepository(session)

    async def create_lead(self, data: LeadCreate) -> Lead:
        """
        Create a new lead and log INGESTED activity.
        """
        logger.info("Creating lead", email=data.email, company=data.company_name)

        lead = await self.lead_repo.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            company_name=data.company_name,
            job_title=data.job_title,
            industry=data.industry,
            company_size=data.company_size,
            country=data.country,
            source=data.source.value if data.source else None,
            budget_range=data.budget_range,
            pain_point=data.pain_point,
            urgency=data.urgency.value if data.urgency else None,
            lead_message=data.lead_message,
            status=LeadStatus.NEW.value,
        )

        await self.activity_repo.create(
            lead_id=lead.id,
            type=ActivityType.INGESTED.value,
            payload={"source": data.source.value if data.source else None},
        )

        logger.info("Lead created", lead_id=str(lead.id))
        return lead

    async def get_lead(self, id: uuid.UUID) -> Lead | None:
        """
        Retrieve a lead by ID.
        """
        return await self.lead_repo.get_by_id(id)

    async def list_leads(
        self,
        filters: dict | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Lead], str | None]:
        """
        List leads with optional filters and pagination.
        Delegates to repository.
        """
        return await self.lead_repo.list(
            filters=filters,
            cursor=cursor,
            limit=limit,
        )

    async def update_lead_status(
        self,
        id: uuid.UUID,
        status: LeadStatus,
    ) -> Lead:
        """
        Update lead status and log STATUS_CHANGED activity.
        """
        lead = await self.lead_repo.get_by_id(id)
        if lead is None:
            raise ValueError(f"Lead {id} not found")

        old_status = lead.status
        logger.info("Updating lead status", lead_id=str(id), old_status=old_status, new_status=status.value)

        lead = await self.lead_repo.update(
            lead,
            status=status.value,
        )

        await self.activity_repo.create(
            lead_id=lead.id,
            type=ActivityType.STATUS_CHANGED.value,
            payload={"old_status": old_status, "new_status": status.value},
        )

        logger.info("Lead status updated", lead_id=str(id), new_status=status.value)
        return lead

    async def bulk_create_from_csv(self, rows: list[dict]) -> CSVUploadResponse:
        """
        Bulk create leads from CSV rows.
        Validates each row, sanitizes injection chars (strip leading =+-@),
        creates leads, and returns created count + errors list.
        """
        logger.info("Bulk creating leads from CSV", row_count=len(rows))

        created_count = 0
        errors = []

        for idx, row in enumerate(rows):
            try:
                # Sanitize all string fields to prevent CSV injection
                sanitized_row = self._sanitize_csv_row(row)

                # Validate required fields
                if not sanitized_row.get("first_name"):
                    errors.append({"row": idx + 1, "error": "Missing required field: first_name"})
                    continue
                if not sanitized_row.get("last_name"):
                    errors.append({"row": idx + 1, "error": "Missing required field: last_name"})
                    continue
                if not sanitized_row.get("email"):
                    errors.append({"row": idx + 1, "error": "Missing required field: email"})
                    continue
                if not sanitized_row.get("company_name"):
                    errors.append({"row": idx + 1, "error": "Missing required field: company_name"})
                    continue

                # Create lead data
                lead_data = LeadCreate(
                    first_name=sanitized_row["first_name"],
                    last_name=sanitized_row["last_name"],
                    email=sanitized_row["email"],
                    phone=sanitized_row.get("phone"),
                    company_name=sanitized_row["company_name"],
                    job_title=sanitized_row.get("job_title"),
                    industry=sanitized_row.get("industry"),
                    company_size=sanitized_row.get("company_size"),
                    country=sanitized_row.get("country"),
                    source=sanitized_row.get("source"),
                    budget_range=sanitized_row.get("budget_range"),
                    pain_point=sanitized_row.get("pain_point"),
                    urgency=sanitized_row.get("urgency"),
                    lead_message=sanitized_row.get("lead_message"),
                )

                await self.create_lead(lead_data)
                created_count += 1

            except Exception as e:
                logger.error("Error creating lead from CSV row", row=idx + 1, error=str(e))
                errors.append({"row": idx + 1, "error": str(e)})

        logger.info("Bulk create completed", created=created_count, errors=len(errors))

        return CSVUploadResponse(
            created=created_count,
            errors=errors,
        )

    def _sanitize_csv_row(self, row: dict) -> dict:
        """
        Sanitize CSV row to prevent injection attacks.
        Strips leading =, +, -, @ from all string values.

        Preserves a leading + or - when followed by a digit (e.g. "+1-555"
        is a legitimate phone number, not an injection vector).
        """
        sanitized = {}
        for key, value in row.items():
            if isinstance(value, str):
                # Strip whitespace first
                value = value.strip()
                # Strip leading injection characters, but preserve +/- before digits (phone numbers)
                while value and value[0] in ("=", "+", "-", "@"):
                    if value[0] in ("+", "-") and len(value) > 1 and value[1].isdigit():
                        break
                    value = value[1:]
                sanitized[key] = value if value else None
            else:
                sanitized[key] = value
        return sanitized
