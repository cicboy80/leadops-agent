"""Test CSV sanitization and validation."""

import pytest

from app.services.lead_service import LeadService


def test_strip_injection_chars():
    """Test fields starting with =, +, -, @ get stripped."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "=cmd|'/evil'!A1",
        "last_name": "+John",
        "email": "-user@example.com",
        "company_name": "@EvilCorp",
        "phone": "=1+1+1",
        "normal_field": "This is normal",
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "cmd|'/evil'!A1"
    assert sanitized["last_name"] == "John"
    assert sanitized["email"] == "user@example.com"
    assert sanitized["company_name"] == "EvilCorp"
    assert sanitized["phone"] == "1+1+1"
    assert sanitized["normal_field"] == "This is normal"


def test_multiple_leading_injection_chars():
    """Test multiple leading injection characters are all stripped."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "===+++---@@@Evil",
        "last_name": "Normal",
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "Evil"
    assert sanitized["last_name"] == "Normal"


def test_valid_csv_row():
    """Test normal row passes validation without modification."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "company_name": "Acme Corp",
        "phone": "+1-555-0123",
        "job_title": "CTO",
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "John"
    assert sanitized["last_name"] == "Doe"
    assert sanitized["email"] == "john.doe@example.com"
    assert sanitized["company_name"] == "Acme Corp"
    assert sanitized["phone"] == "+1-555-0123"
    assert sanitized["job_title"] == "CTO"


def test_whitespace_trimming():
    """Test leading/trailing whitespace is removed."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "  John  ",
        "last_name": "\tDoe\t",
        "email": "  john@example.com  ",
        "company_name": " Acme Corp ",
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "John"
    assert sanitized["last_name"] == "Doe"
    assert sanitized["email"] == "john@example.com"
    assert sanitized["company_name"] == "Acme Corp"


def test_empty_string_fields():
    """Test empty strings are handled correctly."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "",
        "last_name": "Doe",
        "email": "   ",
        "company_name": "=",  # Just injection char
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] is None
    assert sanitized["last_name"] == "Doe"
    assert sanitized["email"] is None
    assert sanitized["company_name"] is None


def test_none_values_preserved():
    """Test None values are preserved."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "John",
        "last_name": None,
        "email": "john@example.com",
        "phone": None,
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "John"
    assert sanitized["last_name"] is None
    assert sanitized["email"] == "john@example.com"
    assert sanitized["phone"] is None


def test_non_string_values():
    """Test non-string values are preserved."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "John",
        "age": 35,
        "active": True,
        "score": 85.5,
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "John"
    assert sanitized["age"] == 35
    assert sanitized["active"] is True
    assert sanitized["score"] == 85.5


def test_injection_in_middle_of_string():
    """Test injection chars in middle of string are not stripped."""
    service = LeadService(session=None)  # type: ignore

    test_row = {
        "first_name": "John=Smith",
        "company_name": "Acme+Corp",
        "email": "user-name@example.com",
        "notes": "Contact @manager",
    }

    sanitized = service._sanitize_csv_row(test_row)

    assert sanitized["first_name"] == "John=Smith"
    assert sanitized["company_name"] == "Acme+Corp"
    assert sanitized["email"] == "user-name@example.com"
    assert sanitized["notes"] == "Contact @manager"


def test_all_injection_chars():
    """Test all injection characters (=, +, -, @) are stripped."""
    service = LeadService(session=None)  # type: ignore

    test_cases = [
        ("=Evil", "Evil"),
        ("+Evil", "Evil"),
        ("-Evil", "Evil"),
        ("@Evil", "Evil"),
    ]

    for input_value, expected in test_cases:
        test_row = {"field": input_value}
        sanitized = service._sanitize_csv_row(test_row)
        assert sanitized["field"] == expected, f"Failed for {input_value}"
