import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import (
    ActionType,
    ActivityType,
    DeliveryStatus,
    EmailVariant,
    LeadSource,
    LeadStatus,
    OutcomeStage,
    OutcomeType,
    ReplyClassification,
    ScoreLabel,
    Urgency,
)


# --- Pagination ---


class CursorParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


class PaginatedResponse(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False


# --- Lead ---


class LeadCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    company_name: str = Field(min_length=1, max_length=255)
    job_title: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    source: LeadSource | None = None
    budget_range: str | None = None
    pain_point: str | None = None
    urgency: Urgency | None = None
    lead_message: str | None = None


class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    source: LeadSource | None = None
    budget_range: str | None = None
    pain_point: str | None = None
    urgency: Urgency | None = None
    lead_message: str | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    company_name: str
    job_title: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    source: str | None = None
    budget_range: str | None = None
    pain_point: str | None = None
    urgency: str | None = None
    lead_message: str | None = None

    status: LeadStatus
    score_label: ScoreLabel | None = None
    score_value: int | None = None
    score_rationale: str | None = None
    recommended_action: ActionType | None = None

    enrichment_data: dict | None = None
    score_breakdown: list[dict] | None = None
    processing_status: str

    current_outcome_stage: str | None = None
    outcome_stage_entered_at: datetime | None = None

    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def extract_score_breakdown(self) -> "LeadResponse":
        if self.score_breakdown is None and self.enrichment_data:
            self.score_breakdown = self.enrichment_data.get("score_breakdown")
        return self


class LeadListResponse(PaginatedResponse):
    items: list[LeadResponse]


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


class CSVUploadResponse(BaseModel):
    created: int
    errors: list[dict]


# --- Activity ---


class ActivityResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    type: ActivityType
    payload: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityListResponse(PaginatedResponse):
    items: list[ActivityResponse]


# --- Email Draft ---


class EmailDraftCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    variant: EmailVariant = EmailVariant.FIRST_TOUCH


class EmailDraftResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    subject: str
    body: str
    variant: str
    approved: bool
    sent_at: datetime | None = None
    delivery_status: DeliveryStatus
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    bounced_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailDraftListResponse(PaginatedResponse):
    items: list[EmailDraftResponse]


# --- Feedback ---


class FeedbackCreate(BaseModel):
    outcome: OutcomeType
    notes: str | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    outcome: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Outcome Stage ---


class InboundReplyRequest(BaseModel):
    reply_body: str = Field(min_length=1)
    sender_email: str | None = None


class OutcomeStageResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    stage: str
    previous_stage: str | None = None
    reason: str
    triggered_by: str | None = None
    notes: str | None = None
    metadata_json: dict | None = None
    entered_at: datetime
    exited_at: datetime | None = None

    model_config = {"from_attributes": True}


class OutcomeStageTransitionRequest(BaseModel):
    stage: OutcomeStage
    notes: str | None = None


class OutcomeStageListResponse(BaseModel):
    items: list[OutcomeStageResponse]


class NextStagesResponse(BaseModel):
    current_stage: str | None = None
    next_stages: list[str]


# --- Reply Classification ---


class InboundReplyResponse(BaseModel):
    stage_record: OutcomeStageResponse | None = None
    classification: str
    confidence: float
    reasoning: str
    extracted_dates: list[str] = []
    auto_action_taken: str | None = None


class ReplyClassificationResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    reply_body: str
    classification: str
    confidence: float
    reasoning: str
    extracted_dates: list[str] | None = None
    is_auto_reply: bool = False
    overridden_by: str | None = None
    overridden_classification: str | None = None
    overridden_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReplyClassificationListResponse(BaseModel):
    items: list[ReplyClassificationResponse]


class ClassificationOverrideRequest(BaseModel):
    new_classification: ReplyClassification
    notes: str | None = None


# --- Notification ---


class NotificationResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None = None
    type: str
    title: str
    body: str
    metadata_json: dict | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]


# --- Trace ---


class TraceResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    graph_run_id: str
    node_events: dict | None = None
    llm_inputs: dict | None = None
    llm_outputs: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TraceListResponse(PaginatedResponse):
    items: list[TraceResponse]


# --- Scoring Config ---


class ScoringConfigResponse(BaseModel):
    id: uuid.UUID
    weights: dict
    thresholds: dict
    updated_at: datetime
    updated_by: str | None = None

    model_config = {"from_attributes": True}


class ScoringConfigUpdate(BaseModel):
    weights: dict | None = None
    thresholds: dict | None = None


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    version: str = "0.1.0"


# --- Pipeline Run ---


class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    thread_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    node_timings: dict | None = None

    model_config = {"from_attributes": True}
