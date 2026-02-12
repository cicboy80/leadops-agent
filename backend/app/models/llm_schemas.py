"""Pydantic models for structured LLM output via function calling.

Used with ChatOpenAI(...).with_structured_output(Model).
"""

from pydantic import BaseModel, Field

from app.models.enums import ActionType, EmailVariant, ReplyClassification, ScoreLabel


class ScoreResult(BaseModel):
    """Output of the score_lead node (gpt-4o-mini)."""

    score_value: int = Field(ge=0, le=100, description="Numeric score 0-100")
    score_label: ScoreLabel = Field(description="HOT, WARM, or COLD")
    rationale: str = Field(
        min_length=10,
        description="2-3 sentence explanation of why this score was given",
    )


class DecisionResult(BaseModel):
    """Output of the decide_next_action node (gpt-4o-mini)."""

    action: ActionType = Field(description="SEND_EMAIL, ASK_QUESTION, DISQUALIFY, or HOLD")
    reasoning: str = Field(description="Why this action was chosen")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Fields that would improve scoring if provided",
    )


class EmailDraftResult(BaseModel):
    """Output of the draft_email node (gpt-4o)."""

    subject: str = Field(min_length=5, max_length=200, description="Email subject line")
    body: str = Field(min_length=50, description="Email body text")
    variant: EmailVariant = Field(
        default=EmailVariant.FIRST_TOUCH,
        description="Email variant type",
    )


class ReplyClassificationResult(BaseModel):
    """Output of reply classification (gpt-4o-mini)."""

    classification: ReplyClassification = Field(
        description="Classification of the inbound reply"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(description="Explanation of why this classification was chosen")
    extracted_dates: list[str] = Field(
        default_factory=list,
        description="Any dates or time references extracted from the reply",
    )
    is_auto_reply: bool = Field(
        default=False, description="Whether this appears to be an auto-reply (e.g. OOO)"
    )
