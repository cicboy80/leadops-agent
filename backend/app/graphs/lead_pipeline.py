"""LangGraph state machine for lead processing pipeline.

Flow:
  START → normalize_input → enrich_lead → score_lead → decide_next_action → [conditional]
    if SEND_EMAIL/ASK_QUESTION → draft_email → log_to_crm → END
    if DISQUALIFY/HOLD → log_to_crm → END
"""

from langgraph.graph import END, StateGraph

from app.graphs.nodes.decide import decide_next_action
from app.graphs.nodes.draft_email import draft_email
from app.graphs.nodes.enrich import enrich_lead
from app.graphs.nodes.log_crm import log_to_crm
from app.graphs.nodes.normalize import normalize_input
from app.graphs.nodes.score import score_lead
from app.graphs.routing import route_after_decision
from app.models.graph_state import LeadProcessingState

_compiled_graph = None


def build_graph() -> StateGraph:
    graph = StateGraph(LeadProcessingState)

    graph.add_node("normalize_input", normalize_input)
    graph.add_node("enrich_lead", enrich_lead)
    graph.add_node("score_lead", score_lead)
    graph.add_node("decide_next_action", decide_next_action)
    graph.add_node("draft_email", draft_email)
    graph.add_node("log_to_crm", log_to_crm)

    graph.set_entry_point("normalize_input")
    graph.add_edge("normalize_input", "enrich_lead")
    graph.add_edge("enrich_lead", "score_lead")
    graph.add_edge("score_lead", "decide_next_action")
    graph.add_conditional_edges(
        "decide_next_action",
        route_after_decision,
        {"draft_email": "draft_email", "log_to_crm": "log_to_crm"},
    )
    graph.add_edge("draft_email", "log_to_crm")
    graph.add_edge("log_to_crm", END)

    return graph


def get_graph():  # noqa: ANN201
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph
