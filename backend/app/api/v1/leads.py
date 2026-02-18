"""Lead management endpoints."""

import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ensure_demo_leads,
    get_current_user,
    get_lead_service,
    get_outcome_service,
    get_pipeline_service,
    get_reply_classification_service,
)
from app.models.enums import LeadSource, LeadStatus, ScoreLabel
from app.models.schemas import (
    CSVUploadResponse,
    ClassificationOverrideRequest,
    FeedbackCreate,
    FeedbackResponse,
    InboundReplyRequest,
    InboundReplyResponse,
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    NextStagesResponse,
    OutcomeStageListResponse,
    OutcomeStageResponse,
    OutcomeStageTransitionRequest,
    PipelineRunResponse,
    ReplyClassificationListResponse,
    ReplyClassificationResponse,
)
from app.services.lead_service import LeadService
from app.services.outcome_service import OutcomeService
from app.services.pipeline_service import PipelineService
from app.services.reply_classification_service import ReplyClassificationService

router = APIRouter()


def sanitize_csv_cell(value: str) -> str:
    """Strip leading formula injection characters from CSV cells."""
    if value and len(value) > 0 and value[0] in ("=", "+", "-", "@"):
        return value[1:]
    return value


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, tags=["leads"])
async def create_lead(
    lead: LeadCreate,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> LeadResponse:
    """Create a new lead manually."""
    result = await lead_service.create_lead(lead)
    if demo_session_id:
        result.demo_session_id = demo_session_id
        await lead_service.session.flush()
    return LeadResponse.model_validate(result)


@router.post("/upload", response_model=CSVUploadResponse, status_code=status.HTTP_201_CREATED, tags=["leads"])
async def upload_leads_csv(
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> CSVUploadResponse:
    """Upload and parse a CSV file of leads.

    Expected columns: first_name, last_name, email, company_name, and optional fields.
    Validates and sanitizes against CSV injection attacks.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    try:
        contents = await file.read()
        text_content = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        )

    csv_reader = csv.DictReader(io.StringIO(text_content))
    rows = []

    required_fields = {"first_name", "last_name", "email", "company_name"}
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):
        sanitized_row = {k: sanitize_csv_cell(v) if v else v for k, v in row.items()}

        missing = required_fields - set(sanitized_row.keys())
        if missing:
            errors.append({
                "row": row_num,
                "error": f"Missing required fields: {', '.join(missing)}",
            })
            continue

        empty_fields = [f for f in required_fields if not sanitized_row.get(f, "").strip()]
        if empty_fields:
            errors.append({
                "row": row_num,
                "error": f"Empty required fields: {', '.join(empty_fields)}",
            })
            continue

        rows.append(sanitized_row)

    if len(rows) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 rows per upload",
        )

    result = await lead_service.bulk_create_from_csv(rows, demo_session_id=demo_session_id)
    # Merge pre-parse errors with service errors
    result.errors = errors + result.errors
    return result


@router.get("/", response_model=LeadListResponse, tags=["leads"])
async def list_leads(
    lead_status: Annotated[LeadStatus | None, Query(alias="status")] = None,
    score_label: Annotated[ScoreLabel | None, Query()] = None,
    source: Annotated[LeadSource | None, Query()] = None,
    outcome_stage: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> LeadListResponse:
    """List leads with optional filtering and cursor-based pagination."""
    filters: dict = {}
    if demo_session_id:
        filters["demo_session_id"] = demo_session_id
    if lead_status:
        filters["status"] = lead_status.value
    if score_label:
        filters["score_label"] = score_label.value
    if source:
        filters["source"] = source.value
    if outcome_stage:
        # Cumulative filter: include leads that have progressed past the requested stage.
        # Pipeline: EMAIL_SENT → RESPONDED → BOOKED_DEMO → CLOSED_WON/CLOSED_LOST
        cumulative_stages: dict[str, list[str]] = {
            "EMAIL_SENT": ["EMAIL_SENT", "RESPONDED", "BOOKED_DEMO", "CLOSED_WON", "CLOSED_LOST"],
            "RESPONDED": ["RESPONDED", "BOOKED_DEMO", "CLOSED_WON", "CLOSED_LOST"],
            "BOOKED_DEMO": ["BOOKED_DEMO", "CLOSED_WON"],
        }
        filters["current_outcome_stage"] = cumulative_stages.get(outcome_stage, [outcome_stage])

    items, next_cursor = await lead_service.list_leads(
        filters=filters if filters else None,
        cursor=cursor,
        limit=limit,
    )

    return LeadListResponse(
        items=[LeadResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.get("/{lead_id}", response_model=LeadResponse, tags=["leads"])
async def get_lead(
    lead_id: uuid.UUID,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> LeadResponse:
    """Get a single lead by ID."""
    lead = await lead_service.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if demo_session_id and lead.demo_session_id != demo_session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.post("/{lead_id}/run", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED, tags=["leads"])
async def run_pipeline_for_lead(
    lead_id: uuid.UUID,
    user: str = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> PipelineRunResponse:
    """Trigger the agentic pipeline for a specific lead.

    Returns immediately with a pipeline run record; actual processing is async.
    """
    try:
        pipeline_run = await pipeline_service.run_pipeline(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return PipelineRunResponse.model_validate(pipeline_run)


@router.post("/{lead_id}/status", tags=["leads"])
async def update_lead_status(
    lead_id: uuid.UUID,
    status_update: dict,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> LeadResponse:
    """Update lead status."""
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status field required")
    try:
        lead_status = LeadStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {new_status}")
    try:
        lead = await lead_service.update_lead_status(lead_id, lead_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return LeadResponse.model_validate(lead)


@router.post("/{lead_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED, tags=["leads"])
async def submit_feedback(
    lead_id: uuid.UUID,
    feedback: FeedbackCreate,
    user: str = Depends(get_current_user),
    lead_service: LeadService = Depends(get_lead_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> FeedbackResponse:
    """Submit outcome feedback for a lead.

    Used to train the scoring weight adjustment logic.
    """
    from app.repositories.feedback_repository import FeedbackRepository
    from app.services.scoring_config_service import ScoringConfigService

    # Verify lead exists
    lead = await lead_service.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # Create feedback record
    feedback_repo = FeedbackRepository(lead_service.session)
    fb = await feedback_repo.create(
        lead_id=lead_id,
        outcome=feedback.outcome.value,
        notes=feedback.notes,
    )

    # Trigger learning update if lead has a score
    if lead.score_value is not None:
        scoring_service = ScoringConfigService(lead_service.session)
        await scoring_service.update_weights_from_feedback(
            outcome=feedback.outcome.value,
            lead_score=lead.score_value,
        )

    return FeedbackResponse.model_validate(fb)


@router.get("/{lead_id}/outcome-stages", response_model=OutcomeStageListResponse, tags=["leads"])
async def get_outcome_stages(
    lead_id: uuid.UUID,
    user: str = Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> OutcomeStageListResponse:
    """Get the full outcome stage history timeline for a lead."""
    try:
        history = await outcome_service.get_history(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return OutcomeStageListResponse(
        items=[OutcomeStageResponse.model_validate(s) for s in history],
    )


@router.post(
    "/{lead_id}/outcome-stages",
    response_model=OutcomeStageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["leads"],
)
async def transition_outcome_stage(
    lead_id: uuid.UUID,
    body: OutcomeStageTransitionRequest,
    user: str = Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> OutcomeStageResponse:
    """Manually transition a lead to a new outcome stage."""
    try:
        record = await outcome_service.transition_stage(
            lead_id=lead_id,
            new_stage=body.stage,
            notes=body.notes,
            triggered_by="user",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return OutcomeStageResponse.model_validate(record)


@router.post(
    "/{lead_id}/inbound-reply",
    response_model=InboundReplyResponse,
    status_code=status.HTTP_200_OK,
    tags=["leads"],
)
async def inbound_reply(
    lead_id: uuid.UUID,
    body: InboundReplyRequest,
    user: str = Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> InboundReplyResponse:
    """Handle a simulated inbound email reply with LLM classification.

    Classifies the reply, auto-routes to the correct stage, and returns
    classification details.
    """
    try:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead_id,
            reply_body=body.reply_body,
            sender_email=body.sender_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    stage_response = None
    if result["stage_record"] is not None:
        stage_response = OutcomeStageResponse.model_validate(result["stage_record"])

    return InboundReplyResponse(
        stage_record=stage_response,
        classification=result["classification"],
        confidence=result["confidence"],
        reasoning=result["reasoning"],
        extracted_dates=result["extracted_dates"],
        auto_action_taken=result["auto_action_taken"],
    )


@router.get(
    "/{lead_id}/classifications",
    response_model=ReplyClassificationListResponse,
    tags=["leads"],
)
async def get_classifications(
    lead_id: uuid.UUID,
    user: str = Depends(get_current_user),
    classification_service: ReplyClassificationService = Depends(get_reply_classification_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> ReplyClassificationListResponse:
    """Get reply classification history for a lead."""
    records = await classification_service.get_all_classifications(lead_id)
    return ReplyClassificationListResponse(
        items=[ReplyClassificationResponse.model_validate(r) for r in records],
    )


@router.post(
    "/{lead_id}/classifications/{classification_id}/override",
    response_model=ReplyClassificationResponse,
    tags=["leads"],
)
async def override_classification(
    lead_id: uuid.UUID,
    classification_id: uuid.UUID,
    body: ClassificationOverrideRequest,
    user: str = Depends(get_current_user),
    classification_service: ReplyClassificationService = Depends(get_reply_classification_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> ReplyClassificationResponse:
    """Override a reply classification with a manual correction."""
    try:
        record = await classification_service.override_classification(
            classification_id=classification_id,
            new_classification=body.new_classification,
            overridden_by="user",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ReplyClassificationResponse.model_validate(record)


@router.get("/{lead_id}/next-stages", response_model=NextStagesResponse, tags=["leads"])
async def get_next_stages(
    lead_id: uuid.UUID,
    user: str = Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
) -> NextStagesResponse:
    """Get valid next outcome stages for a lead."""
    try:
        current, next_stages = await outcome_service.get_valid_next_stages(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return NextStagesResponse(current_stage=current, next_stages=next_stages)


@router.post("/bulk-run", status_code=status.HTTP_202_ACCEPTED, tags=["leads"])
async def bulk_run_pipeline(
    lead_ids: list[uuid.UUID],
    user: str = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    demo_session_id: str | None = Depends(ensure_demo_leads),
    lead_service: LeadService = Depends(get_lead_service),
) -> dict:
    """Trigger the agentic pipeline for multiple leads.

    Maximum 100 leads per request.
    """
    if len(lead_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 leads per bulk run request",
        )

    # Verify session ownership when in demo mode
    if demo_session_id:
        for lid in lead_ids:
            lead = await lead_service.get_lead(lid)
            if lead is None or lead.demo_session_id != demo_session_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Lead {lid} does not belong to this demo session",
                )

    results = []
    errors = []
    for lead_id in lead_ids:
        try:
            run = await pipeline_service.run_pipeline(lead_id)
            results.append(str(run.id))
        except Exception as e:
            errors.append({"lead_id": str(lead_id), "error": str(e)})

    return {"pipeline_runs": results, "errors": errors}
