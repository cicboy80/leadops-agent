"""Decide next action node — determines routing decision based on lead score."""

import time

from app.core.llm import get_llm, has_llm_key
from app.models.graph_state import LeadProcessingState
from app.models.llm_schemas import DecisionResult


async def decide_next_action(state: LeadProcessingState) -> dict:
    """Decide the next action for the lead.

    If LLM key available: uses get_llm("fast").with_structured_output(DecisionResult)
    Fallback: deterministic rules based on score_label and missing fields
    - HOT -> SEND_EMAIL
    - WARM with missing fields -> ASK_QUESTION
    - WARM -> SEND_EMAIL
    - COLD -> DISQUALIFY
    """
    start = time.time()

    lead = state["lead"]
    score = state.get("score")
    enrichment = state.get("enrichment", {})
    errors = []

    decision_result = None

    if has_llm_key() and score:
        try:
            # Build LLM prompt
            prompt = f"""Based on this lead's score and data, decide the next action.

Lead Data:
- Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
- Email: {lead.get('email', '')}
- Company: {lead.get('company_name', '')}
- Job Title: {lead.get('job_title', 'N/A')}
- Industry: {lead.get('industry', 'N/A')}
- Company Size: {lead.get('company_size', 'N/A')}
- Budget Range: {lead.get('budget_range', 'N/A')}
- Pain Point: {lead.get('pain_point', 'N/A')}
- Urgency: {lead.get('urgency', 'N/A')}

Score:
- Value: {score['score_value']}
- Label: {score['score_label']}
- Rationale: {score['rationale']}

Choose one action:
- SEND_EMAIL: High quality lead, ready for outreach
- ASK_QUESTION: Promising lead but needs more information
- DISQUALIFY: Low quality, not a good fit
- HOLD: Decent lead but not ready for outreach now

Identify any missing fields that would improve scoring."""

            llm = get_llm("fast").with_structured_output(DecisionResult)
            result = await llm.ainvoke(prompt)

            decision_result = {
                "action": result.action.value,
                "reasoning": result.reasoning,
                "missing_fields": result.missing_fields or [],
            }

        except Exception as e:
            errors.append(f"LLM decision failed: {str(e)}, falling back to rule-based")

    # Fallback: rule-based decision
    if decision_result is None:
        score_label = score["score_label"] if score else "COLD"

        # Check for missing important fields
        important_fields = ["job_title", "budget_range", "pain_point", "urgency"]
        missing_fields = [
            field for field in important_fields if not lead.get(field) or not str(lead[field]).strip()
        ]

        # Decision logic
        if score_label == "HOT":
            action = "SEND_EMAIL"
            reasoning = "Hot lead with strong indicators, ready for immediate outreach"
        elif score_label == "WARM":
            if missing_fields:
                action = "ASK_QUESTION"
                reasoning = f"Warm lead with potential, but missing key information: {', '.join(missing_fields)}"
            else:
                action = "SEND_EMAIL"
                reasoning = "Warm lead with sufficient information for outreach"
        else:  # COLD
            action = "DISQUALIFY"
            reasoning = "Cold lead with low quality indicators, not a good fit"

        decision_result = {
            "action": action,
            "reasoning": reasoning,
            "missing_fields": missing_fields,
        }

    elapsed = time.time() - start

    return {
        "decision": decision_result,
        "errors": errors,
        "node_timings": {**state.get("node_timings", {}), "decide_next_action": elapsed},
    }
