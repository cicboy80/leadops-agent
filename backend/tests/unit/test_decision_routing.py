"""Test decision routing logic for LangGraph conditional edges."""

from app.graphs.routing import route_after_decision
from app.models.graph_state import LeadProcessingState


def test_route_send_email():
    """Test SEND_EMAIL decision routes to draft_email."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "SEND_EMAIL",
            "reasoning": "Hot lead ready for outreach",
            "missing_fields": [],
        },
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "draft_email"


def test_route_ask_question():
    """Test ASK_QUESTION decision routes to draft_email."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "ASK_QUESTION",
            "reasoning": "Need more information from lead",
            "missing_fields": ["budget_range"],
        },
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "draft_email"


def test_route_disqualify():
    """Test DISQUALIFY decision routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "DISQUALIFY",
            "reasoning": "Lead does not meet qualification criteria",
            "missing_fields": [],
        },
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"


def test_route_hold():
    """Test HOLD decision routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "HOLD",
            "reasoning": "Wait for more information before acting",
            "missing_fields": ["company_size", "industry"],
        },
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"


def test_route_with_errors():
    """Test state with errors routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "SEND_EMAIL",
            "reasoning": "This should be ignored due to errors",
            "missing_fields": [],
        },
        "email_draft": None,
        "errors": ["Scoring failed", "Enrichment timeout"],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"


def test_route_no_decision():
    """Test missing decision routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": None,
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"


def test_route_empty_decision():
    """Test empty decision dict routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {},  # type: ignore
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"


def test_route_invalid_action():
    """Test invalid action routes to log_to_crm."""
    state: LeadProcessingState = {
        "lead_id": "test-lead-id",
        "lead": {},
        "enrichment": {},
        "score": None,
        "decision": {
            "action": "INVALID_ACTION",
            "reasoning": "This action doesn't exist",
            "missing_fields": [],
        },
        "email_draft": None,
        "errors": [],
        "trace_id": "test-trace",
        "node_timings": {},
    }

    result = route_after_decision(state)
    assert result == "log_to_crm"
