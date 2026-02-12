"""Draft email node — generates personalized email content."""

import time

from app.core.llm import get_llm, has_llm_key
from app.models.graph_state import LeadProcessingState
from app.models.llm_schemas import EmailDraftResult


async def draft_email(state: LeadProcessingState) -> dict:
    """Draft personalized email for the lead.

    If LLM key available: uses get_llm("quality").with_structured_output(EmailDraftResult)
    Fallback: template-based drafting
    """
    start = time.time()

    lead = state["lead"]
    score = state.get("score")
    decision = state.get("decision")
    errors = []

    email_draft = None

    if has_llm_key():
        try:
            # Build LLM prompt
            action = decision["action"] if decision else "SEND_EMAIL"

            prompt = f"""Draft a professional B2B outreach email for this lead.

Lead Data:
- Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
- Company: {lead.get('company_name', '')}
- Job Title: {lead.get('job_title', 'N/A')}
- Industry: {lead.get('industry', 'N/A')}
- Pain Point: {lead.get('pain_point', 'N/A')}
- Lead Message: {lead.get('lead_message', 'N/A')}

Score: {score['score_value']} ({score['score_label']}) - {score['rationale']}

Action: {action}
Reasoning: {decision['reasoning'] if decision else 'N/A'}

Email Guidelines:
- Keep it concise (3-4 short paragraphs)
- Personalize based on their company and role
- Reference their pain point if provided
- Include a clear call-to-action
- Professional but conversational tone
- If action is ASK_QUESTION, focus on gathering missing information: {decision.get('missing_fields', []) if decision else []}

Write an engaging subject line and email body."""

            llm = get_llm("quality").with_structured_output(EmailDraftResult)
            result = await llm.ainvoke(prompt)

            email_draft = {
                "subject": result.subject,
                "body": result.body,
                "variant": result.variant.value,
            }

        except Exception as e:
            errors.append(f"LLM email drafting failed: {str(e)}, falling back to template")

    # Fallback: template-based email
    if email_draft is None:
        first_name = lead.get("first_name", "there")
        company = lead.get("company_name", "your company")
        pain_point = lead.get("pain_point", "")
        action = decision["action"] if decision else "SEND_EMAIL"
        missing_fields = decision.get("missing_fields", []) if decision else []

        if action == "ASK_QUESTION" and missing_fields:
            subject = f"Quick question about {company}"
            body = f"""Hi {first_name},

I came across {company} and wanted to learn more about your team's needs.

To better understand how we can help, could you share a bit more about:
{chr(10).join(f"- Your {field.replace('_', ' ')}" for field in missing_fields[:3])}

Looking forward to connecting.

Best regards,
Sales Team"""
        else:
            subject = f"Helping {company} achieve better results"
            pain_section = f"\n\nI noticed you mentioned: {pain_point}\n" if pain_point else ""

            body = f"""Hi {first_name},

I'm reaching out because I believe we can help {company} overcome some of the challenges you might be facing.{pain_section}

Our platform has helped similar companies in your industry achieve significant improvements. I'd love to schedule a brief call to explore how we can support your goals.

Would you be available for a 15-minute conversation this week?

Best regards,
Sales Team"""

        email_draft = {
            "subject": subject,
            "body": body,
            "variant": "first_touch",
        }

    elapsed = time.time() - start

    return {
        "email_draft": email_draft,
        "errors": errors,
        "node_timings": {**state.get("node_timings", {}), "draft_email": elapsed},
    }
