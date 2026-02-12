"""Test EmailDraftResult Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.models.enums import EmailVariant
from app.models.llm_schemas import EmailDraftResult


def test_valid_draft():
    """Test valid email draft result."""
    draft = EmailDraftResult(
        subject="Great opportunity for Acme Corp",
        body="Hi John,\n\nI wanted to reach out about our lead automation solution. "
             "Based on your interest, I think we could help you reduce manual work "
             "by 80%. Would you be available for a quick call next week?\n\nBest regards,\nSales Team",
        variant=EmailVariant.FIRST_TOUCH,
    )

    assert len(draft.subject) >= 5
    assert len(draft.body) >= 50
    assert draft.variant == EmailVariant.FIRST_TOUCH


def test_draft_minimum_subject_length():
    """Test subject meets minimum length requirement."""
    draft = EmailDraftResult(
        subject="Hello",  # Exactly 5 characters (minimum)
        body="This is a valid email body that is definitely longer than fifty characters total.",
        variant=EmailVariant.FIRST_TOUCH,
    )

    assert len(draft.subject) == 5


def test_draft_short_subject():
    """Test subject too short raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        EmailDraftResult(
            subject="Hi",  # Less than 5 characters
            body="This is a valid email body that is definitely longer than fifty characters total.",
            variant=EmailVariant.FIRST_TOUCH,
        )

    assert "subject" in str(exc_info.value)


def test_draft_subject_too_long():
    """Test subject exceeds maximum length."""
    with pytest.raises(ValidationError) as exc_info:
        EmailDraftResult(
            subject="A" * 201,  # 201 characters (max is 200)
            body="This is a valid email body that is definitely longer than fifty characters total.",
            variant=EmailVariant.FIRST_TOUCH,
        )

    assert "subject" in str(exc_info.value)


def test_draft_minimum_body_length():
    """Test body meets minimum length requirement."""
    draft = EmailDraftResult(
        subject="Valid subject",
        body="X" * 50,  # Exactly 50 characters (minimum)
        variant=EmailVariant.FIRST_TOUCH,
    )

    assert len(draft.body) == 50


def test_draft_short_body():
    """Test body too short raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        EmailDraftResult(
            subject="Valid subject",
            body="Too short",  # Less than 50 characters
            variant=EmailVariant.FIRST_TOUCH,
        )

    assert "body" in str(exc_info.value)


def test_draft_missing_fields():
    """Test missing required fields raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        EmailDraftResult(
            subject="Valid subject",
            # Missing body
            variant=EmailVariant.FIRST_TOUCH,
        )  # type: ignore

    assert "body" in str(exc_info.value)


def test_draft_all_variants():
    """Test all valid email variants."""
    variants = [
        EmailVariant.FIRST_TOUCH,
        EmailVariant.FOLLOW_UP_1,
        EmailVariant.FOLLOW_UP_2,
        EmailVariant.BREAKUP,
    ]

    for variant in variants:
        draft = EmailDraftResult(
            subject="Test subject for variant",
            body="This is a test email body that is long enough to pass validation requirements.",
            variant=variant,
        )
        assert draft.variant == variant


def test_draft_default_variant():
    """Test default variant is FIRST_TOUCH."""
    draft = EmailDraftResult(
        subject="Test subject",
        body="This is a test email body that is long enough to pass validation requirements.",
        # variant not provided
    )

    assert draft.variant == EmailVariant.FIRST_TOUCH


def test_draft_invalid_variant():
    """Test invalid variant raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        EmailDraftResult(
            subject="Test subject",
            body="This is a test email body that is long enough to pass validation requirements.",
            variant="invalid_variant",  # type: ignore
        )

    assert "variant" in str(exc_info.value)


def test_draft_to_dict():
    """Test EmailDraftResult can be converted to dict."""
    draft = EmailDraftResult(
        subject="Test conversion",
        body="This is a test email body for dict conversion that is long enough.",
        variant=EmailVariant.FOLLOW_UP_1,
    )

    draft_dict = draft.model_dump()

    assert draft_dict["subject"] == "Test conversion"
    assert "dict conversion" in draft_dict["body"]
    assert draft_dict["variant"] == EmailVariant.FOLLOW_UP_1


def test_draft_with_special_characters():
    """Test email draft with special characters in subject and body."""
    draft = EmailDraftResult(
        subject="Re: Your inquiry about LeadOps Agent 🚀",
        body="Hi John,\n\n"
             "Thank you for your interest! Here's what we can do:\n"
             "• Automate lead qualification\n"
             "• Reduce manual work by 80%\n"
             "• Integrate with your CRM\n\n"
             "Let's schedule a demo!\n\n"
             "Best regards,\nThe Team",
        variant=EmailVariant.FIRST_TOUCH,
    )

    assert "🚀" in draft.subject
    assert "•" in draft.body
    assert "\n" in draft.body


def test_draft_multiline_body():
    """Test email draft with multiline body."""
    body_text = """Hi John,

I hope this email finds you well. I wanted to reach out regarding your interest in lead automation.

Based on your company size and industry, I believe we can help you:
1. Reduce qualification time
2. Improve lead quality
3. Scale your sales operations

Would you be available for a quick 15-minute call next week?

Best regards,
Sales Team"""

    draft = EmailDraftResult(
        subject="Lead automation for your team",
        body=body_text,
        variant=EmailVariant.FIRST_TOUCH,
    )

    assert len(draft.body.split("\n")) > 5
    assert draft.body == body_text
