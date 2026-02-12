"""LangGraph state TypedDict — in-memory during graph execution only.

Never conflate with ORM models or API schemas.
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


def merge_errors(existing: list[str], new: list[str]) -> list[str]:
    return existing + new


class LeadData(TypedDict, total=False):
    """Lead data extracted from the database for graph processing."""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    company_name: str
    job_title: str
    industry: str
    company_size: str
    country: str
    source: str
    budget_range: str
    pain_point: str
    urgency: str
    lead_message: str


class ScoreResult(TypedDict):
    score_value: int
    score_label: str
    rationale: str


class DecisionResult(TypedDict):
    action: str
    reasoning: str
    missing_fields: list[str]


class EmailDraftData(TypedDict):
    subject: str
    body: str
    variant: str


class LeadProcessingState(TypedDict):
    """Full state for the lead processing graph."""

    lead: LeadData
    enrichment: dict[str, Any]
    score: ScoreResult | None
    decision: DecisionResult | None
    email_draft: EmailDraftData | None
    errors: Annotated[list[str], merge_errors]
    trace_id: str
    lead_id: str
    node_timings: dict[str, float]
