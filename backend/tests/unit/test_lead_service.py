"""Test lead service business logic."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.models.enums import ActivityType, LeadSource, LeadStatus, Urgency
from app.models.orm import Lead
from app.models.schemas import LeadCreate
from app.services.lead_service import LeadService


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_lead_repo():
    """Create a mock lead repository."""
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    """Create a mock activity repository."""
    return AsyncMock()


@pytest.fixture
def lead_service(mock_session, mock_lead_repo, mock_activity_repo):
    """Create LeadService with mocked repositories."""
    service = LeadService(mock_session)
    service.lead_repo = mock_lead_repo
    service.activity_repo = mock_activity_repo
    return service


@pytest.mark.asyncio
async def test_create_lead(lead_service, mock_lead_repo, mock_activity_repo):
    """Test creating a new lead."""
    lead_id = uuid.uuid4()

    # Mock the repository response
    mock_lead = Lead(
        id=lead_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@acmecorp.com",
        company_name="Acme Corp",
        status=LeadStatus.NEW.value,
        processing_status="IDLE",
    )
    mock_lead_repo.create.return_value = mock_lead

    # Create lead data
    lead_data = LeadCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@acmecorp.com",
        phone="+1-555-0123",
        company_name="Acme Corp",
        job_title="Director of Engineering",
        industry="SaaS",
        company_size="100-500",
        country="USA",
        source=LeadSource.WEB_FORM,
        budget_range="$50k-$100k",
        pain_point="Need to automate lead qualification",
        urgency=Urgency.HIGH,
        lead_message="Looking for a solution",
    )

    # Call service method
    result = await lead_service.create_lead(lead_data)

    # Verify repository was called correctly
    mock_lead_repo.create.assert_called_once()
    call_kwargs = mock_lead_repo.create.call_args.kwargs
    assert call_kwargs["first_name"] == "John"
    assert call_kwargs["last_name"] == "Doe"
    assert call_kwargs["email"] == "john.doe@acmecorp.com"
    assert call_kwargs["company_name"] == "Acme Corp"
    assert call_kwargs["status"] == LeadStatus.NEW.value

    # Verify activity was logged
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["lead_id"] == lead_id
    assert activity_kwargs["type"] == ActivityType.INGESTED.value
    assert activity_kwargs["payload"]["source"] == "web_form"

    # Verify result
    assert result.id == lead_id
    assert result.first_name == "John"


@pytest.mark.asyncio
async def test_get_lead(lead_service, mock_lead_repo):
    """Test retrieving a lead by ID."""
    lead_id = uuid.uuid4()

    mock_lead = Lead(
        id=lead_id,
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        company_name="Example Inc",
        status=LeadStatus.NEW.value,
        processing_status="IDLE",
    )
    mock_lead_repo.get_by_id.return_value = mock_lead

    result = await lead_service.get_lead(lead_id)

    mock_lead_repo.get_by_id.assert_called_once_with(lead_id)
    assert result.id == lead_id
    assert result.first_name == "Jane"


@pytest.mark.asyncio
async def test_get_lead_not_found(lead_service, mock_lead_repo):
    """Test retrieving a non-existent lead returns None."""
    lead_id = uuid.uuid4()
    mock_lead_repo.get_by_id.return_value = None

    result = await lead_service.get_lead(lead_id)

    assert result is None


@pytest.mark.asyncio
async def test_list_leads(lead_service, mock_lead_repo):
    """Test listing leads with pagination."""
    mock_leads = [
        Lead(
            id=uuid.uuid4(),
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            company_name="Example Corp",
            status=LeadStatus.NEW.value,
            processing_status="IDLE",
        ),
        Lead(
            id=uuid.uuid4(),
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            company_name="Test Inc",
            status=LeadStatus.QUALIFIED.value,
            processing_status="IDLE",
        ),
    ]

    mock_lead_repo.list.return_value = (mock_leads, "next_cursor_token")

    results, cursor = await lead_service.list_leads(
        filters={"status": "NEW"},
        cursor=None,
        limit=50,
    )

    mock_lead_repo.list.assert_called_once_with(
        filters={"status": "NEW"},
        cursor=None,
        limit=50,
    )
    assert len(results) == 2
    assert cursor == "next_cursor_token"


@pytest.mark.asyncio
async def test_update_lead_status(lead_service, mock_lead_repo, mock_activity_repo):
    """Test updating lead status."""
    lead_id = uuid.uuid4()

    mock_lead = Lead(
        id=lead_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        company_name="Example Corp",
        status=LeadStatus.NEW.value,
        processing_status="IDLE",
    )

    updated_lead = Lead(
        id=lead_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        company_name="Example Corp",
        status=LeadStatus.QUALIFIED.value,
        processing_status="IDLE",
    )

    mock_lead_repo.get_by_id.return_value = mock_lead
    mock_lead_repo.update.return_value = updated_lead

    result = await lead_service.update_lead_status(lead_id, LeadStatus.QUALIFIED)

    # Verify status was updated
    mock_lead_repo.update.assert_called_once()
    assert result.status == LeadStatus.QUALIFIED.value

    # Verify activity was logged
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["lead_id"] == lead_id
    assert activity_kwargs["type"] == ActivityType.STATUS_CHANGED.value
    assert activity_kwargs["payload"]["old_status"] == LeadStatus.NEW.value
    assert activity_kwargs["payload"]["new_status"] == LeadStatus.QUALIFIED.value


@pytest.mark.asyncio
async def test_update_lead_status_not_found(lead_service, mock_lead_repo):
    """Test updating status for non-existent lead raises error."""
    lead_id = uuid.uuid4()
    mock_lead_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Lead .* not found"):
        await lead_service.update_lead_status(lead_id, LeadStatus.QUALIFIED)


def test_sanitize_injection_chars(lead_service):
    """Test CSV injection character sanitization."""
    test_row = {
        "first_name": "=Evil",
        "last_name": "+Malicious",
        "email": "-hacker@example.com",
        "company_name": "@BadCorp",
        "normal_field": "Safe Value",
    }

    result = lead_service._sanitize_csv_row(test_row)

    assert result["first_name"] == "Evil"
    assert result["last_name"] == "Malicious"
    assert result["email"] == "hacker@example.com"
    assert result["company_name"] == "BadCorp"
    assert result["normal_field"] == "Safe Value"


def test_sanitize_whitespace(lead_service):
    """Test whitespace trimming in CSV sanitization."""
    test_row = {
        "first_name": "  John  ",
        "last_name": "\tDoe\t",
        "email": " john@example.com ",
    }

    result = lead_service._sanitize_csv_row(test_row)

    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"
    assert result["email"] == "john@example.com"


def test_sanitize_preserves_none(lead_service):
    """Test None values are preserved during sanitization."""
    test_row = {
        "first_name": "John",
        "last_name": None,
        "phone": None,
    }

    result = lead_service._sanitize_csv_row(test_row)

    assert result["first_name"] == "John"
    assert result["last_name"] is None
    assert result["phone"] is None
