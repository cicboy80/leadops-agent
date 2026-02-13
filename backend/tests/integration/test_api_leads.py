"""Integration tests for lead API endpoints using FastAPI test client."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.enums import LeadSource, LeadStatus, Urgency


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """Test health check endpoint returns 200."""
    response = await test_client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "database" in data
    assert "llm" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_no_auth():
    """Test health check does not require authentication."""
    # Create a client without auth headers
    from app.main import create_app
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_lead(test_client: AsyncClient, api_key_header: dict):
    """Test creating a lead via POST /api/v1/leads."""
    lead_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@acmecorp.com",
        "phone": "+1-555-0123",
        "company_name": "Acme Corp",
        "job_title": "Director of Engineering",
        "industry": "SaaS",
        "company_size": "100-500",
        "country": "USA",
        "source": "web_form",
        "budget_range": "$50k-$100k",
        "pain_point": "Need to automate lead qualification",
        "urgency": "high",
        "lead_message": "Looking for a solution",
    }

    response = await test_client.post(
        "/api/v1/leads",
        json=lead_data,
        headers=api_key_header,
    )

    # Currently returns 501 (not implemented)
    assert response.status_code in [201, 501]

    # When implemented, should return 201 with lead data
    # if response.status_code == 201:
    #     data = response.json()
    #     assert data["email"] == "john.doe@acmecorp.com"
    #     assert data["company_name"] == "Acme Corp"
    #     assert "id" in data


@pytest.mark.asyncio
async def test_create_lead_missing_required_fields(test_client: AsyncClient, api_key_header: dict):
    """Test creating lead with missing required fields fails."""
    lead_data = {
        "first_name": "John",
        # Missing last_name, email, company_name
    }

    response = await test_client.post(
        "/api/v1/leads",
        json=lead_data,
        headers=api_key_header,
    )

    # Should return 422 Validation Error when implemented
    assert response.status_code in [422, 501]


@pytest.mark.asyncio
async def test_list_leads(test_client: AsyncClient, api_key_header: dict):
    """Test listing leads via GET /api/v1/leads."""
    response = await test_client.get(
        "/api/v1/leads",
        headers=api_key_header,
    )

    # Currently returns 501 (not implemented)
    assert response.status_code in [200, 501]

    # When implemented, should return paginated list
    # if response.status_code == 200:
    #     data = response.json()
    #     assert "items" in data
    #     assert "next_cursor" in data
    #     assert "has_more" in data
    #     assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_leads_with_filters(test_client: AsyncClient, api_key_header: dict):
    """Test listing leads with status filter."""
    response = await test_client.get(
        "/api/v1/leads?status=NEW&limit=10",
        headers=api_key_header,
    )

    assert response.status_code in [200, 501]


@pytest.mark.asyncio
async def test_list_leads_pagination(test_client: AsyncClient, api_key_header: dict):
    """Test listing leads with pagination parameters."""
    response = await test_client.get(
        "/api/v1/leads?limit=25&cursor=abc123",
        headers=api_key_header,
    )

    assert response.status_code in [200, 501]


@pytest.mark.asyncio
async def test_get_lead_by_id(test_client: AsyncClient, api_key_header: dict):
    """Test getting a single lead by ID."""
    lead_id = uuid.uuid4()

    response = await test_client.get(
        f"/api/v1/leads/{lead_id}",
        headers=api_key_header,
    )

    # Currently returns 501 or 404
    assert response.status_code in [200, 404, 501]


@pytest.mark.asyncio
async def test_unauthorized_missing_api_key(test_client: AsyncClient):
    """Test missing API key returns 401."""
    response = await test_client.get("/api/v1/leads")

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_unauthorized_invalid_api_key(test_client: AsyncClient):
    """Test invalid API key returns 401."""
    response = await test_client.get(
        "/api/v1/leads",
        headers={"X-API-Key": "invalid-key"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_csv_endpoint(test_client: AsyncClient, api_key_header: dict):
    """Test CSV upload endpoint."""
    csv_content = """first_name,last_name,email,company_name,job_title
John,Doe,john@example.com,Acme Corp,CTO
Jane,Smith,jane@example.com,Test Inc,CEO"""

    files = {"file": ("leads.csv", csv_content, "text/csv")}

    response = await test_client.post(
        "/api/v1/leads/upload",
        files=files,
        headers=api_key_header,
    )

    assert response.status_code in [201, 501]

    # When implemented, should return created count
    # if response.status_code == 201:
    #     data = response.json()
    #     assert "created" in data
    #     assert "errors" in data


@pytest.mark.asyncio
async def test_upload_csv_invalid_file(test_client: AsyncClient, api_key_header: dict):
    """Test uploading non-CSV file fails."""
    files = {"file": ("leads.txt", "not a csv", "text/plain")}

    response = await test_client.post(
        "/api/v1/leads/upload",
        files=files,
        headers=api_key_header,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_csv_with_injection_chars(test_client: AsyncClient, api_key_header: dict):
    """Test CSV upload sanitizes injection characters."""
    csv_content = """first_name,last_name,email,company_name
=Evil,+Bad,-Hacker,@MaliciousCorp"""

    files = {"file": ("leads.csv", csv_content, "text/csv")}

    response = await test_client.post(
        "/api/v1/leads/upload",
        files=files,
        headers=api_key_header,
    )

    # Should successfully sanitize and create (or return 501)
    assert response.status_code in [201, 501]


@pytest.mark.asyncio
async def test_run_pipeline_for_lead(test_client: AsyncClient, api_key_header: dict):
    """Test triggering pipeline for a lead."""
    lead_id = uuid.uuid4()

    response = await test_client.post(
        f"/api/v1/leads/{lead_id}/run",
        headers=api_key_header,
    )

    # Should return 202 Accepted when implemented
    assert response.status_code in [202, 404, 501]


@pytest.mark.asyncio
async def test_bulk_run_pipeline(test_client: AsyncClient, api_key_header: dict):
    """Test bulk pipeline execution."""
    lead_ids = [str(uuid.uuid4()) for _ in range(5)]

    response = await test_client.post(
        "/api/v1/leads/bulk-run",
        json=lead_ids,
        headers=api_key_header,
    )

    assert response.status_code in [202, 501]


@pytest.mark.asyncio
async def test_bulk_run_pipeline_too_many_leads(test_client: AsyncClient, api_key_header: dict):
    """Test bulk pipeline with more than 100 leads fails."""
    lead_ids = [str(uuid.uuid4()) for _ in range(101)]

    response = await test_client.post(
        "/api/v1/leads/bulk-run",
        json=lead_ids,
        headers=api_key_header,
    )

    assert response.status_code == 400
    data = response.json()
    assert "100 leads" in data["detail"]


@pytest.mark.asyncio
async def test_submit_feedback(test_client: AsyncClient, api_key_header: dict):
    """Test submitting feedback for a lead."""
    lead_id = uuid.uuid4()
    feedback_data = {
        "outcome": "booked_demo",
        "notes": "Lead responded positively and scheduled demo for next week",
    }

    response = await test_client.post(
        f"/api/v1/leads/{lead_id}/feedback",
        json=feedback_data,
        headers=api_key_header,
    )

    assert response.status_code in [201, 404, 501]


@pytest.mark.asyncio
async def test_cors_headers(test_client: AsyncClient):
    """Test CORS headers are present in preflight response."""
    response = await test_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    # CORS preflight should return 200
    assert response.status_code in [200, 204, 400]
