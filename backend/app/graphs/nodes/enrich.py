"""Enrich lead node — adds heuristic enrichment data."""

import time

from app.models.graph_state import LeadProcessingState


async def enrich_lead(state: LeadProcessingState) -> dict:
    """Enrich lead with additional data via heuristic enrichment.

    Calls enrichment_service.enrich(lead_data) to perform heuristic enrichment
    based on email domain, company name patterns, etc.
    """
    start = time.time()

    lead = state["lead"]

    # Heuristic enrichment based on available data
    enrichment = {}

    # Email domain enrichment
    email = lead.get("email", "")
    if email and "@" in email:
        domain = email.split("@")[1].lower()
        enrichment["email_domain"] = domain

        # Detect free email providers
        free_domains = {
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "aol.com",
        }
        enrichment["is_free_email"] = domain in free_domains

    # Company size heuristics
    company_size = lead.get("company_size", "").lower()
    if company_size:
        if any(term in company_size for term in ["enterprise", "1000+", "large"]):
            enrichment["company_size_category"] = "enterprise"
        elif any(term in company_size for term in ["mid", "100-1000", "medium"]):
            enrichment["company_size_category"] = "mid-market"
        else:
            enrichment["company_size_category"] = "small"
    else:
        enrichment["company_size_category"] = "unknown"

    # Industry enrichment
    industry = lead.get("industry", "").lower()
    if industry:
        tech_keywords = [
            "software",
            "saas",
            "tech",
            "it",
            "digital",
            "cloud",
            "ai",
            "ml",
        ]
        enrichment["is_tech_industry"] = any(kw in industry for kw in tech_keywords)

    # Budget signal
    budget = lead.get("budget_range", "")
    enrichment["has_budget"] = bool(budget and budget.strip())

    # Pain point signal — check both structured field and lead message
    pain_point = lead.get("pain_point", "")
    lead_message = lead.get("lead_message", "")
    has_pain_from_field = bool(pain_point and pain_point.strip())
    has_pain_from_message = False
    if lead_message:
        msg_lower = lead_message.lower()
        pain_keywords = [
            "losing", "struggling", "challenge", "problem", "pain",
            "frustrat", "slow", "inefficien", "costly", "expensive",
            "manual", "bottleneck", "failing", "behind", "difficult",
        ]
        has_pain_from_message = any(kw in msg_lower for kw in pain_keywords)
    enrichment["has_pain_point"] = has_pain_from_field or has_pain_from_message

    # Urgency mapping — check both structured field and lead message
    urgency = lead.get("urgency", "").lower()
    if urgency in ["low", "medium", "high"]:
        enrichment["urgency_level"] = urgency
    elif lead_message:
        msg_lower = lead_message.lower()
        urgency_high_keywords = ["urgent", "asap", "immediately", "critical", "losing", "deadline"]
        urgency_medium_keywords = ["soon", "looking for", "need", "want to", "interested"]
        if any(kw in msg_lower for kw in urgency_high_keywords):
            enrichment["urgency_level"] = "high"
        elif any(kw in msg_lower for kw in urgency_medium_keywords):
            enrichment["urgency_level"] = "medium"
        else:
            enrichment["urgency_level"] = "low"
    else:
        enrichment["urgency_level"] = "low"

    # Job title seniority
    job_title = lead.get("job_title", "").lower()
    senior_titles = [
        "ceo", "cto", "cfo", "coo", "cmo", "cio", "cpo",
        "founder", "co-founder", "owner", "president",
        "vp", "vice president",
        "director", "head of",
        "partner", "managing",
    ]
    mid_titles = ["manager", "lead", "senior", "principal"]
    if any(t in job_title for t in senior_titles):
        enrichment["seniority"] = "senior"
    elif any(t in job_title for t in mid_titles):
        enrichment["seniority"] = "mid"
    else:
        enrichment["seniority"] = "junior"

    elapsed = time.time() - start

    return {
        "enrichment": enrichment,
        "node_timings": {**state.get("node_timings", {}), "enrich_lead": elapsed},
    }
