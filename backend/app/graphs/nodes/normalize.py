"""Normalize input node — validates and sanitizes lead data."""

import time

from app.models.graph_state import LeadProcessingState


async def normalize_input(state: LeadProcessingState) -> dict:
    """Normalize and validate lead input data.

    - Strips whitespace from all string fields
    - Lowercases email
    - Validates required fields (first_name, last_name, email, company_name)
    - Sanitizes CSV injection chars (strips leading =, +, -, @ from string fields)
    - Records timing
    """
    start = time.time()

    lead = state["lead"]
    errors = []

    # Required fields validation
    required_fields = ["first_name", "last_name", "email", "company_name"]
    for field in required_fields:
        if not lead.get(field) or not str(lead[field]).strip():
            errors.append(f"Missing required field: {field}")

    # Normalize and sanitize
    normalized_lead = {}
    csv_injection_chars = {"=", "+", "-", "@"}

    for key, value in lead.items():
        if isinstance(value, str):
            # Strip whitespace
            value = value.strip()

            # Sanitize CSV injection
            if value and value[0] in csv_injection_chars:
                value = value.lstrip("=+-@")

            # Lowercase email
            if key == "email":
                value = value.lower()

            normalized_lead[key] = value
        else:
            normalized_lead[key] = value

    elapsed = time.time() - start

    return {
        "lead": normalized_lead,
        "errors": errors,
        "node_timings": {**state.get("node_timings", {}), "normalize_input": elapsed},
    }
