import structlog

logger = structlog.get_logger()

# Personal email domains
PERSONAL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "protonmail.com",
    "mail.com",
}

# Company size mapping
COMPANY_SIZE_MAP = {
    "1-10": "small",
    "11-50": "small",
    "51-200": "medium",
    "201-500": "medium",
    "501-1000": "large",
    "1001+": "enterprise",
    "1000+": "enterprise",
}

# Region mapping by country
REGION_MAP = {
    "US": "North America",
    "USA": "North America",
    "United States": "North America",
    "CA": "North America",
    "Canada": "North America",
    "MX": "North America",
    "Mexico": "North America",
    "UK": "Europe",
    "United Kingdom": "Europe",
    "GB": "Europe",
    "DE": "Europe",
    "Germany": "Europe",
    "FR": "Europe",
    "France": "Europe",
    "ES": "Europe",
    "Spain": "Europe",
    "IT": "Europe",
    "Italy": "Europe",
    "NL": "Europe",
    "Netherlands": "Europe",
    "SE": "Europe",
    "Sweden": "Europe",
    "NO": "Europe",
    "Norway": "Europe",
    "DK": "Europe",
    "Denmark": "Europe",
    "FI": "Europe",
    "Finland": "Europe",
    "PL": "Europe",
    "Poland": "Europe",
    "AU": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "NZ": "Asia-Pacific",
    "New Zealand": "Asia-Pacific",
    "JP": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "CN": "Asia-Pacific",
    "China": "Asia-Pacific",
    "IN": "Asia-Pacific",
    "India": "Asia-Pacific",
    "SG": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
    "HK": "Asia-Pacific",
    "Hong Kong": "Asia-Pacific",
    "KR": "Asia-Pacific",
    "Korea": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
}


def enrich_lead(lead_data: dict) -> dict:
    """
    Perform heuristic enrichment on lead data.

    Infers:
    - company_type from email domain (personal vs corporate)
    - company_size_category from company_size string
    - region from country

    No external API calls - all heuristic-based.

    Args:
        lead_data: Dictionary containing lead fields

    Returns:
        Dictionary with enrichment fields
    """
    enrichment = {}

    logger.info("Enriching lead", email=lead_data.get("email"))

    # Infer company type from email domain
    email = lead_data.get("email", "")
    if email and "@" in email:
        domain = email.split("@")[1].lower()
        if domain in PERSONAL_DOMAINS:
            enrichment["company_type"] = "personal"
        else:
            enrichment["company_type"] = "corporate"
        enrichment["email_domain"] = domain
    else:
        enrichment["company_type"] = "unknown"

    # Estimate company size category from company_size string
    company_size = lead_data.get("company_size", "")
    if company_size:
        # Normalize company_size string
        normalized = company_size.strip()
        enrichment["company_size_category"] = COMPANY_SIZE_MAP.get(
            normalized,
            _infer_company_size_from_text(normalized),
        )
    else:
        enrichment["company_size_category"] = "unknown"

    # Infer region from country
    country = lead_data.get("country", "")
    if country:
        enrichment["region"] = REGION_MAP.get(
            country.strip(),
            "Other",
        )
    else:
        enrichment["region"] = "unknown"

    # Extract job title level if present
    job_title = lead_data.get("job_title", "")
    if job_title:
        enrichment["seniority_level"] = _infer_seniority(job_title)
    else:
        enrichment["seniority_level"] = "unknown"

    logger.info("Enrichment completed", enrichment=enrichment)

    return enrichment


def _infer_company_size_from_text(text: str) -> str:
    """
    Infer company size category from free text.
    """
    text_lower = text.lower()

    if any(term in text_lower for term in ["small", "startup", "1-10", "10-50"]):
        return "small"
    elif any(term in text_lower for term in ["medium", "50-200", "100-500"]):
        return "medium"
    elif any(term in text_lower for term in ["large", "500-1000", "enterprise", "1000+"]):
        return "large"
    else:
        return "unknown"


def _infer_seniority(job_title: str) -> str:
    """
    Infer seniority level from job title.
    """
    title_lower = job_title.lower()

    # Executive level
    if any(term in title_lower for term in ["ceo", "cto", "cfo", "coo", "cmo", "cio", "president", "founder", "owner"]):
        return "executive"

    # VP/Director level
    if any(term in title_lower for term in ["vp", "vice president", "director", "head of"]):
        return "director"

    # Manager level
    if any(term in title_lower for term in ["manager", "lead", "supervisor"]):
        return "manager"

    # Individual contributor
    if any(term in title_lower for term in ["senior", "sr", "principal", "staff"]):
        return "senior"
    elif any(term in title_lower for term in ["junior", "jr", "associate", "assistant"]):
        return "junior"
    else:
        return "mid"
