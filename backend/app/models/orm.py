import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_status", "status"),
        Index("ix_leads_score_label", "score_label"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_current_outcome_stage", "current_outcome_stage"),
        Index("ix_leads_demo_session_id", "demo_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    company_size: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(50))
    budget_range: Mapped[str | None] = mapped_column(String(100))
    pain_point: Mapped[str | None] = mapped_column(Text)
    urgency: Mapped[str | None] = mapped_column(String(20))
    lead_message: Mapped[str | None] = mapped_column(Text)

    # Scoring
    status: Mapped[str] = mapped_column(String(30), default="NEW")
    score_label: Mapped[str | None] = mapped_column(String(10))
    score_value: Mapped[int | None] = mapped_column()
    score_rationale: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(String(30))

    # Enrichment
    enrichment_data: Mapped[dict | None] = mapped_column(JSON)

    # Processing
    processing_status: Mapped[str] = mapped_column(String(20), default="IDLE")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Outcome stage tracking
    current_outcome_stage: Mapped[str | None] = mapped_column(String(30))
    outcome_stage_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Demo session isolation
    demo_session_id: Mapped[str | None] = mapped_column(String(36))

    # Relationships
    activities: Mapped[list["ActivityLog"]] = relationship(back_populates="lead", lazy="selectin")
    email_drafts: Mapped[list["EmailDraft"]] = relationship(back_populates="lead", lazy="selectin")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="lead", lazy="selectin")
    traces: Mapped[list["Trace"]] = relationship(back_populates="lead", lazy="selectin")
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="lead", lazy="selectin"
    )
    outcome_stages: Mapped[list["LeadOutcomeStage"]] = relationship(
        back_populates="lead", lazy="selectin"
    )
    reply_classifications: Mapped[list["ReplyClassificationRecord"]] = relationship(
        back_populates="lead", lazy="select"
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_logs_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="activities")


class EmailDraft(Base):
    __tablename__ = "email_drafts"
    __table_args__ = (Index("ix_email_drafts_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variant: Mapped[str] = mapped_column(String(30), default="first_touch")
    approved: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery tracking
    delivery_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="email_drafts")


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (Index("ix_feedbacks_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="feedbacks")


class Trace(Base):
    __tablename__ = "traces"
    __table_args__ = (Index("ix_traces_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    graph_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    node_events: Mapped[dict | None] = mapped_column(JSON)
    llm_inputs: Mapped[dict | None] = mapped_column(JSON)  # PII-redacted
    llm_outputs: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="traces")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (Index("ix_pipeline_runs_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    node_timings: Mapped[dict | None] = mapped_column(JSON)

    lead: Mapped["Lead"] = relationship(back_populates="pipeline_runs")


class LeadOutcomeStage(Base):
    __tablename__ = "lead_outcome_stages"
    __table_args__ = (
        Index("ix_lead_outcome_stages_lead_id", "lead_id"),
        Index("ix_lead_outcome_stages_stage", "stage"),
        Index("ix_lead_outcome_stages_entered_at", "entered_at"),
        Index("ix_lead_outcome_stages_lead_id_stage", "lead_id", "stage"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_stage: Mapped[str | None] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(30), nullable=False)  # AUTOMATIC, MANUAL, SYSTEM
    triggered_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lead: Mapped["Lead"] = relationship(back_populates="outcome_stages")


class ScoringConfig(Base):
    __tablename__ = "scoring_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(255))


class ReplyClassificationRecord(Base):
    __tablename__ = "reply_classifications"
    __table_args__ = (Index("ix_reply_classifications_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=False
    )
    reply_body: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_dates: Mapped[dict | None] = mapped_column(JSON)
    is_auto_reply: Mapped[bool] = mapped_column(default=False)
    overridden_by: Mapped[str | None] = mapped_column(String(255))
    overridden_classification: Mapped[str | None] = mapped_column(String(30))
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="reply_classifications")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_lead_id", "lead_id"),
        Index("ix_notifications_read_at", "read_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    demo_session_id: Mapped[str | None] = mapped_column(String(36))
