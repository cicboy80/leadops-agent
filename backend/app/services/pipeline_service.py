import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityType, ProcessingStatus, PipelineRunStatus
from app.models.orm import Lead, PipelineRun
from app.repositories.activity_repository import ActivityRepository
from app.repositories.email_draft_repository import EmailDraftRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.pipeline_run_repository import PipelineRunRepository
from app.repositories.trace_repository import TraceRepository

logger = structlog.get_logger()


class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.pipeline_run_repo = PipelineRunRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.email_draft_repo = EmailDraftRepository(session)
        self.trace_repo = TraceRepository(session)

    async def run_pipeline(self, lead_id: uuid.UUID) -> PipelineRun:
        """
        Run the lead processing pipeline for a given lead.

        Creates PipelineRun, sets processing status, builds initial state,
        invokes the compiled graph, updates Lead with results, creates
        activity logs, email drafts, and traces, then returns PipelineRun.
        """
        lead = await self.lead_repo.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} not found")

        # Create thread_id with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        thread_id = f"{lead_id}_{timestamp}"

        logger.info("Starting pipeline run", lead_id=str(lead_id), thread_id=thread_id)

        # Create PipelineRun record
        pipeline_run = await self.pipeline_run_repo.create(
            lead_id=lead_id,
            thread_id=thread_id,
            status=PipelineRunStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        # Set lead processing status to PROCESSING
        await self.lead_repo.update(lead, processing_status=ProcessingStatus.PROCESSING.value)

        try:
            # Import graph here to avoid circular imports
            from app.graphs.lead_pipeline import get_graph

            # Build initial LeadProcessingState from Lead ORM object
            initial_state = self._build_initial_state(lead)

            # Get and invoke the compiled graph
            graph = get_graph()
            result = await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}},
            )

            # Update Lead with results from pipeline
            await self._update_lead_from_result(lead, result)

            # Create activity logs for each step
            await self._log_pipeline_activities(lead_id, result)

            # Create EmailDraft if one was generated
            if result.get("email_draft"):
                await self._create_email_draft_from_result(lead_id, result["email_draft"])

            # Create Trace record with redacted PII
            await self._create_trace(lead_id, thread_id, result)

            # Update PipelineRun to COMPLETED
            await self.pipeline_run_repo.update(
                pipeline_run,
                status=PipelineRunStatus.COMPLETED.value,
                completed_at=datetime.utcnow(),
                node_timings=result.get("node_timings"),
            )

            # Set lead processing status to IDLE
            await self.lead_repo.update(lead, processing_status=ProcessingStatus.IDLE.value)

            logger.info("Pipeline run completed successfully", lead_id=str(lead_id), thread_id=thread_id)

        except Exception as e:
            logger.error("Pipeline run failed", lead_id=str(lead_id), error=str(e), exc_info=True)

            # Update PipelineRun to FAILED
            await self.pipeline_run_repo.update(
                pipeline_run,
                status=PipelineRunStatus.FAILED.value,
                completed_at=datetime.utcnow(),
                error_message=str(e),
            )

            # Set lead processing status to FAILED
            await self.lead_repo.update(lead, processing_status=ProcessingStatus.FAILED.value)

            # Log error activity
            await self.activity_repo.create(
                lead_id=lead_id,
                type=ActivityType.ERROR.value,
                payload={"error": str(e), "thread_id": thread_id},
            )

            raise

        return pipeline_run

    def _build_initial_state(self, lead: Lead) -> dict:
        """
        Build initial LeadProcessingState dict from Lead ORM object.
        """
        lead_data = {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "phone": lead.phone,
            "company_name": lead.company_name,
            "job_title": lead.job_title,
            "industry": lead.industry,
            "company_size": lead.company_size,
            "country": lead.country,
            "source": lead.source,
            "budget_range": lead.budget_range,
            "pain_point": lead.pain_point,
            "urgency": lead.urgency,
            "lead_message": lead.lead_message,
        }
        # Replace None values with "" so graph nodes can safely call .lower() etc.
        lead_data = {k: (v if v is not None else "") for k, v in lead_data.items()}

        return {
            "lead_id": str(lead.id),
            "lead": lead_data,
            "enrichment": {},
            "score": None,
            "decision": None,
            "email_draft": None,
            "errors": [],
        }

    async def _update_lead_from_result(self, lead: Lead, result: dict) -> None:
        """
        Update Lead ORM object with score, decision, and enrichment from pipeline result.
        """
        update_data = {}

        if result.get("score"):
            score_data = result["score"]
            update_data["score_value"] = score_data.get("score_value")
            update_data["score_label"] = score_data.get("score_label")
            update_data["score_rationale"] = score_data.get("rationale")

        if result.get("decision"):
            decision_data = result["decision"]
            update_data["recommended_action"] = decision_data.get("action")

        if result.get("enrichment"):
            enrichment = dict(result["enrichment"])
            # Merge score_breakdown into enrichment_data for frontend display
            if result.get("score", {}).get("score_breakdown"):
                enrichment["score_breakdown"] = result["score"]["score_breakdown"]
            update_data["enrichment_data"] = enrichment

        if update_data:
            await self.lead_repo.update(lead, **update_data)

    async def _log_pipeline_activities(self, lead_id: uuid.UUID, result: dict) -> None:
        """
        Create ActivityLog entries for each pipeline step.
        """
        # Log ENRICHED activity if enrichment data present
        if result.get("enrichment"):
            await self.activity_repo.create(
                lead_id=lead_id,
                type=ActivityType.ENRICHED.value,
                payload={"enrichment": result["enrichment"]},
            )

        # Log SCORED activity if score present
        if result.get("score"):
            await self.activity_repo.create(
                lead_id=lead_id,
                type=ActivityType.SCORED.value,
                payload=result["score"],
            )

        # Log EMAIL_DRAFTED activity if email draft present
        if result.get("email_draft"):
            await self.activity_repo.create(
                lead_id=lead_id,
                type=ActivityType.EMAIL_DRAFTED.value,
                payload={
                    "subject": result["email_draft"].get("subject"),
                    "variant": result["email_draft"].get("variant"),
                },
            )

    async def _create_email_draft_from_result(self, lead_id: uuid.UUID, draft_data: dict) -> None:
        """
        Create EmailDraft record from pipeline result.
        """
        await self.email_draft_repo.create(
            lead_id=lead_id,
            subject=draft_data.get("subject", ""),
            body=draft_data.get("body", ""),
            variant=draft_data.get("variant", "first_touch"),
        )

    async def _create_trace(self, lead_id: uuid.UUID, graph_run_id: str, result: dict) -> None:
        """
        Create Trace record with node events and LLM inputs/outputs.
        Note: PII redaction is handled by TraceService.
        """
        from app.services.trace_service import TraceService

        trace_service = TraceService(self.session)

        node_events = result.get("node_events", {})
        llm_inputs = result.get("llm_inputs", {})
        llm_outputs = result.get("llm_outputs", {})

        await trace_service.create_trace(
            lead_id=lead_id,
            graph_run_id=graph_run_id,
            node_events=node_events,
            llm_inputs=llm_inputs,
            llm_outputs=llm_outputs,
        )
