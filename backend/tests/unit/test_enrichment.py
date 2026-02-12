"""Test heuristic enrichment provider."""

import pytest

from app.tools.enrichment_tool import HeuristicEnrichmentProvider


@pytest.mark.asyncio
async def test_corporate_email():
    """Test corporate domain is detected correctly."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="john.doe@acmecorp.com",
        company="Acme Corp",
    )

    assert result["email_domain"] == "acmecorp.com"
    assert result["is_corporate_email"] is True
    assert result["company_type"] == "corporate"
    assert result["enrichment_source"] == "heuristic"


@pytest.mark.asyncio
async def test_personal_email_gmail():
    """Test gmail.com is detected as personal."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="john.doe@gmail.com",
        company="Freelance Consulting",
    )

    assert result["email_domain"] == "gmail.com"
    assert result["is_corporate_email"] is False
    assert result["company_type"] == "personal"
    assert result["estimated_size"] == "small"
    assert result["enrichment_source"] == "heuristic"


@pytest.mark.asyncio
async def test_personal_email_yahoo():
    """Test yahoo.com is detected as personal."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="user@yahoo.com",
        company="Startup",
    )

    assert result["email_domain"] == "yahoo.com"
    assert result["is_corporate_email"] is False
    assert result["company_type"] == "personal"


@pytest.mark.asyncio
async def test_personal_email_hotmail():
    """Test hotmail.com is detected as personal."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="user@hotmail.com",
        company="Small Business",
    )

    assert result["email_domain"] == "hotmail.com"
    assert result["is_corporate_email"] is False


@pytest.mark.asyncio
async def test_enterprise_company_keyword():
    """Test company with 'enterprise' keyword is detected."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="sales@bigcorp.com",
        company="Enterprise Solutions Inc",
    )

    assert result["estimated_size"] == "enterprise"
    assert result["is_corporate_email"] is True


@pytest.mark.asyncio
async def test_enterprise_company_global():
    """Test company with 'global' keyword is detected as enterprise."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="contact@company.com",
        company="Global Tech Holdings",
    )

    assert result["estimated_size"] == "enterprise"


@pytest.mark.asyncio
async def test_enterprise_company_international():
    """Test company with 'international' keyword is detected as enterprise."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="info@business.io",
        company="International Group Corp",
    )

    assert result["estimated_size"] == "enterprise"


@pytest.mark.asyncio
async def test_unknown_company_size():
    """Test corporate email with no size indicators returns unknown."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="john@startup.io",
        company="Startup Co",
    )

    assert result["is_corporate_email"] is True
    assert result["estimated_size"] == "unknown"


@pytest.mark.asyncio
async def test_email_without_at_symbol():
    """Test malformed email without @ symbol."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="invalid-email",
        company="Test Company",
    )

    assert result["email_domain"] == ""
    assert result["is_corporate_email"] is False


@pytest.mark.asyncio
async def test_empty_email():
    """Test empty email string."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="",
        company="Test Company",
    )

    assert result["email_domain"] == ""
    assert result["is_corporate_email"] is False


@pytest.mark.asyncio
async def test_case_insensitive_domain():
    """Test domain detection is case-insensitive."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="USER@GMAIL.COM",
        company="Personal",
    )

    assert result["email_domain"] == "gmail.com"
    assert result["is_corporate_email"] is False


@pytest.mark.asyncio
async def test_case_insensitive_company_keyword():
    """Test company keyword detection is case-insensitive."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="contact@company.com",
        company="ENTERPRISE SOFTWARE INC",
    )

    assert result["estimated_size"] == "enterprise"


@pytest.mark.asyncio
async def test_all_personal_domains():
    """Test all personal email domains are detected."""
    provider = HeuristicEnrichmentProvider()

    personal_domains = [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "mail.com",
        "protonmail.com",
    ]

    for domain in personal_domains:
        result = await provider.enrich(
            email=f"user@{domain}",
            company="Test",
        )
        assert result["is_corporate_email"] is False, f"Failed for {domain}"
        assert result["company_type"] == "personal", f"Failed for {domain}"


@pytest.mark.asyncio
async def test_all_enterprise_keywords():
    """Test all enterprise keywords are detected."""
    provider = HeuristicEnrichmentProvider()

    keywords = ["enterprise", "global", "international", "corp", "inc", "group", "holdings", "capital"]

    for keyword in keywords:
        result = await provider.enrich(
            email="contact@company.com",
            company=f"Test {keyword} Company",
        )
        assert result["estimated_size"] == "enterprise", f"Failed for keyword: {keyword}"


@pytest.mark.asyncio
async def test_enrichment_result_structure():
    """Test enrichment result has all expected fields."""
    provider = HeuristicEnrichmentProvider()

    result = await provider.enrich(
        email="test@example.com",
        company="Example Corp",
    )

    expected_keys = [
        "email_domain",
        "is_corporate_email",
        "company_type",
        "estimated_size",
        "enrichment_source",
    ]

    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
