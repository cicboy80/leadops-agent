"""Score lead node — calculates lead score using LLM or rule-based fallback."""

import time

from app.core.llm import get_llm, has_llm_key
from app.models.graph_state import LeadProcessingState
from app.models.llm_schemas import ScoreResult


def _build_enrichment_breakdown(enrichment: dict, lead: dict) -> list[dict]:
    """Build a score factor breakdown from enrichment signals for display."""
    breakdown = []

    urgency = enrichment.get("urgency_level", "low")
    urgency_pts = {"high": 25, "medium": 15}.get(urgency, 5)
    breakdown.append({"factor": "Urgency Keywords", "points": urgency_pts, "max": 25})

    pain_pts = 15 if enrichment.get("has_pain_point") else 0
    breakdown.append({"factor": "Pain Point Signal", "points": pain_pts, "max": 15})

    seniority = enrichment.get("seniority", "junior")
    sen_pts = {"senior": 20, "mid": 10}.get(seniority, 0)
    breakdown.append({"factor": "Job Title Seniority", "points": sen_pts, "max": 20})

    company_size_cat = enrichment.get("company_size_category", "unknown")
    co_pts = {"enterprise": 15, "mid-market": 10, "small": 5}.get(company_size_cat, 0)
    breakdown.append({"factor": "Company Size", "points": co_pts, "max": 15})

    budget_pts = 10 if enrichment.get("has_budget") else 0
    breakdown.append({"factor": "Budget Indicator", "points": budget_pts, "max": 10})

    email_pts = 5 if (enrichment.get("is_free_email") is False and enrichment.get("email_domain")) else 0
    breakdown.append({"factor": "Business Email", "points": email_pts, "max": 5})

    tech_pts = 5 if enrichment.get("is_tech_industry") else 0
    breakdown.append({"factor": "Industry Match", "points": tech_pts, "max": 5})

    source = lead.get("source", "").lower()
    source_pts = {"referral": 5, "event": 4, "partner": 4, "web_form": 3, "outbound": 2}.get(source, 0)
    breakdown.append({"factor": "Source Quality", "points": source_pts, "max": 5})

    breakdown.sort(key=lambda x: x["points"], reverse=True)
    return breakdown


async def score_lead(state: LeadProcessingState) -> dict:
    """Score the lead using LLM or rule-based fallback.

    If LLM key available: uses get_llm("fast").with_structured_output(ScoreResult)
    Fallback: rule-based scoring based on urgency, budget, pain_point, company_size, source
    """
    start = time.time()

    lead = state["lead"]
    enrichment = state.get("enrichment", {})
    errors = []

    score_result = None

    if has_llm_key():
        try:
            # Build LLM prompt
            prompt = f"""Score this B2B lead from 0-100 based on quality and likelihood to convert.

Lead Data:
- Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
- Email: {lead.get('email', '')}
- Company: {lead.get('company_name', '')}
- Job Title: {lead.get('job_title', 'N/A')}
- Industry: {lead.get('industry', 'N/A')}
- Company Size: {lead.get('company_size', 'N/A')}
- Country: {lead.get('country', 'N/A')}
- Source: {lead.get('source', 'N/A')}
- Budget Range: {lead.get('budget_range', 'N/A')}
- Pain Point: {lead.get('pain_point', 'N/A')}
- Urgency: {lead.get('urgency', 'N/A')}
- Lead Message: {lead.get('lead_message', 'N/A')}

Enrichment:
- Email Domain: {enrichment.get('email_domain', 'N/A')}
- Is Free Email: {enrichment.get('is_free_email', False)}
- Company Size Category: {enrichment.get('company_size_category', 'unknown')}
- Is Tech Industry: {enrichment.get('is_tech_industry', False)}
- Has Budget: {enrichment.get('has_budget', False)}
- Has Pain Point: {enrichment.get('has_pain_point', False)}

Provide a score 0-100, label (HOT/WARM/COLD), and 2-3 sentence rationale."""

            llm = get_llm("fast").with_structured_output(ScoreResult)
            result = await llm.ainvoke(prompt)

            # Build a heuristic breakdown for display alongside LLM score
            llm_breakdown = _build_enrichment_breakdown(enrichment, lead)

            score_result = {
                "score_value": result.score_value,
                "score_label": result.score_label.value,
                "rationale": result.rationale,
                "score_breakdown": llm_breakdown,
            }

        except Exception as e:
            errors.append(f"LLM scoring failed: {str(e)}, falling back to rule-based")

    # Fallback: rule-based scoring
    if score_result is None:
        score_value = 0
        factors = []
        breakdown = []

        # Urgency scoring (max 25)
        urgency = enrichment.get("urgency_level", "low")
        if urgency == "high":
            pts = 25
        elif urgency == "medium":
            pts = 15
        else:
            pts = 5
        score_value += pts
        factors.append(f"urgency={urgency}(+{pts})")
        breakdown.append({"factor": "Urgency Keywords", "points": pts, "max": 25})

        # Pain point presence (+15)
        pain_pts = 15 if enrichment.get("has_pain_point") else 0
        score_value += pain_pts
        if pain_pts:
            factors.append(f"pain_point(+{pain_pts})")
        breakdown.append({"factor": "Pain Point Signal", "points": pain_pts, "max": 15})

        # Job title seniority (max 20)
        seniority = enrichment.get("seniority", "junior")
        if seniority == "senior":
            sen_pts = 20
        elif seniority == "mid":
            sen_pts = 10
        else:
            sen_pts = 0
        score_value += sen_pts
        if sen_pts:
            factors.append(f"seniority={seniority}(+{sen_pts})")
        breakdown.append({"factor": "Job Title Seniority", "points": sen_pts, "max": 20})

        # Company size (max 15)
        company_size_cat = enrichment.get("company_size_category", "unknown")
        if company_size_cat == "enterprise":
            co_pts = 15
        elif company_size_cat == "mid-market":
            co_pts = 10
        elif company_size_cat == "small":
            co_pts = 5
        else:
            co_pts = 0
        score_value += co_pts
        if co_pts:
            factors.append(f"company={company_size_cat}(+{co_pts})")
        breakdown.append({"factor": "Company Size", "points": co_pts, "max": 15})

        # Budget presence (+10)
        budget_pts = 10 if enrichment.get("has_budget") else 0
        score_value += budget_pts
        if budget_pts:
            factors.append(f"budget(+{budget_pts})")
        breakdown.append({"factor": "Budget Indicator", "points": budget_pts, "max": 10})

        # Business email domain (+5)
        email_pts = 5 if (enrichment.get("is_free_email") is False and enrichment.get("email_domain")) else 0
        score_value += email_pts
        if email_pts:
            factors.append("business_email(+5)")
        breakdown.append({"factor": "Business Email", "points": email_pts, "max": 5})

        # Tech industry (+5)
        tech_pts = 5 if enrichment.get("is_tech_industry") else 0
        score_value += tech_pts
        if tech_pts:
            factors.append("tech_industry(+5)")
        breakdown.append({"factor": "Industry Match", "points": tech_pts, "max": 5})

        # Source (max 5)
        source = lead.get("source", "").lower()
        source_scores = {
            "referral": 5,
            "event": 4,
            "partner": 4,
            "web_form": 3,
            "outbound": 2,
        }
        source_pts = source_scores.get(source, 0)
        if source_pts:
            score_value += source_pts
            factors.append(f"source={source}(+{source_pts})")
        breakdown.append({"factor": "Source Quality", "points": source_pts, "max": 5})

        # Determine label
        if score_value >= 65:
            score_label = "HOT"
        elif score_value >= 40:
            score_label = "WARM"
        else:
            score_label = "COLD"

        # Sort breakdown by points descending for display
        breakdown.sort(key=lambda x: x["points"], reverse=True)

        score_result = {
            "score_value": min(score_value, 100),
            "score_label": score_label,
            "rationale": f"Rule-based score: {', '.join(factors)}",
            "score_breakdown": breakdown,
        }

    elapsed = time.time() - start

    return {
        "score": score_result,
        "errors": errors,
        "node_timings": {**state.get("node_timings", {}), "score_lead": elapsed},
    }
