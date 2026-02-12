"""Enrichment tool — heuristic + optional provider interface."""

from typing import Protocol


class EnrichmentProvider(Protocol):
    async def enrich(self, email: str, company: str) -> dict: ...


class HeuristicEnrichmentProvider:
    """Heuristic enrichment based on email domain and company patterns."""

    PERSONAL_DOMAINS = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "aol.com", "icloud.com", "mail.com", "protonmail.com",
    }

    ENTERPRISE_KEYWORDS = {
        "enterprise", "global", "international", "corp", "inc",
        "group", "holdings", "capital",
    }

    async def enrich(self, email: str, company: str) -> dict:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        company_lower = company.lower()

        is_personal_email = domain in self.PERSONAL_DOMAINS
        is_corporate = not is_personal_email and bool(domain)

        company_type = "personal" if is_personal_email else "corporate"

        size_estimate = "unknown"
        if any(kw in company_lower for kw in self.ENTERPRISE_KEYWORDS):
            size_estimate = "enterprise"
        elif is_personal_email:
            size_estimate = "small"

        return {
            "email_domain": domain,
            "is_corporate_email": is_corporate,
            "company_type": company_type,
            "estimated_size": size_estimate,
            "enrichment_source": "heuristic",
        }


def get_enrichment_provider() -> EnrichmentProvider:
    return HeuristicEnrichmentProvider()
