"""Log to CRM node — marks activity for CRM persistence."""

import time

from app.models.enums import ActivityType
from app.models.graph_state import LeadProcessingState


async def log_to_crm(state: LeadProcessingState) -> dict:
    """Log lead processing activity to CRM.

    This is a thin wrapper in the graph context. It marks that CRM logging should happen
    by adding activity data to state for the service layer to persist after graph completes.
    """
    start = time.time()

    lead = state["lead"]
    score = state.get("score")
    decision = state.get("decision")
    email_draft = state.get("email_draft")

    # Prepare activity metadata for CRM logging
    activity_data = {
        "lead_id": state.get("lead_id"),
        "trace_id": state.get("trace_id"),
        "activity_type": ActivityType.SCORED.value,
        "metadata": {
            "score_value": score["score_value"] if score else None,
            "score_label": score["score_label"] if score else None,
            "decision_action": decision["action"] if decision else None,
            "decision_reasoning": decision["reasoning"] if decision else None,
            "has_email_draft": email_draft is not None,
            "node_timings": state.get("node_timings", {}),
        },
    }

    elapsed = time.time() - start

    return {
        "crm_activity": activity_data,
        "node_timings": {**state.get("node_timings", {}), "log_to_crm": elapsed},
    }
