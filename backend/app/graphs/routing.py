"""Conditional edge functions for the lead processing graph."""

from app.models.graph_state import LeadProcessingState


def route_after_decision(state: LeadProcessingState) -> str:
    """Route based on decision action.

    SEND_EMAIL/ASK_QUESTION → draft_email
    DISQUALIFY/HOLD → log_to_crm
    """
    if state.get("errors"):
        return "log_to_crm"

    decision = state.get("decision")
    if not decision:
        return "log_to_crm"

    action = decision.get("action", "")
    if action in ("SEND_EMAIL", "ASK_QUESTION"):
        return "draft_email"
    return "log_to_crm"
