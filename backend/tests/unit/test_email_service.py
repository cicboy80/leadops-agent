"""Test email service — draft creation, approval, and mock sending."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import ActivityType, DeliveryStatus, EmailVariant, LeadStatus
from app.models.orm import EmailDraft, Lead
from app.services.email_service import EmailService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_email_draft_repo():
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock()


@pytest.fixture
def mock_lead_repo():
    return AsyncMock()


@pytest.fixture
def email_service(mock_session, mock_email_draft_repo, mock_activity_repo, mock_lead_repo):
    service = EmailService(mock_session)
    service.email_draft_repo = mock_email_draft_repo
    service.activity_repo = mock_activity_repo
    service.lead_repo = mock_lead_repo
    return service


def _make_draft(lead_id=None, **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        lead_id=lead_id or uuid.uuid4(),
        subject="Test Subject",
        body="Test body content",
        variant="first_touch",
        approved=False,
        delivery_status=DeliveryStatus.PENDING.value,
    )
    defaults.update(kwargs)
    return EmailDraft(**defaults)


def _make_lead(lead_id=None):
    return Lead(
        id=lead_id or uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email="jane@acme.com",
        company_name="Acme Corp",
        status=LeadStatus.QUALIFIED.value,
        processing_status="IDLE",
    )


# --- create_draft ---


@pytest.mark.asyncio
async def test_create_draft(email_service, mock_email_draft_repo, mock_activity_repo):
    lead_id = uuid.uuid4()
    draft = _make_draft(lead_id=lead_id)
    mock_email_draft_repo.create.return_value = draft

    result = await email_service.create_draft(
        lead_id=lead_id,
        subject="Hello from LeadOps",
        body="We'd love to help you...",
        variant="first_touch",
    )

    mock_email_draft_repo.create.assert_called_once()
    kwargs = mock_email_draft_repo.create.call_args.kwargs
    assert kwargs["lead_id"] == lead_id
    assert kwargs["subject"] == "Hello from LeadOps"
    assert kwargs["variant"] == "first_touch"
    assert kwargs["approved"] is False

    # Activity logged
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["type"] == ActivityType.EMAIL_DRAFTED.value


@pytest.mark.asyncio
async def test_create_draft_invalid_variant_falls_back(email_service, mock_email_draft_repo, mock_activity_repo):
    lead_id = uuid.uuid4()
    mock_email_draft_repo.create.return_value = _make_draft(lead_id=lead_id)

    await email_service.create_draft(
        lead_id=lead_id,
        subject="Test",
        body="Body",
        variant="invalid_variant",
    )

    kwargs = mock_email_draft_repo.create.call_args.kwargs
    assert kwargs["variant"] == EmailVariant.FIRST_TOUCH.value


# --- get_drafts ---


@pytest.mark.asyncio
async def test_get_drafts(email_service, mock_email_draft_repo):
    lead_id = uuid.uuid4()
    drafts = [_make_draft(lead_id=lead_id), _make_draft(lead_id=lead_id)]
    mock_email_draft_repo.list.return_value = (drafts, "cursor-xyz")

    result, cursor = await email_service.get_drafts(lead_id=lead_id, limit=20)

    mock_email_draft_repo.list.assert_called_once_with(
        filters={"lead_id": lead_id}, cursor=None, limit=20
    )
    assert len(result) == 2
    assert cursor == "cursor-xyz"


# --- approve_and_send ---


@pytest.mark.asyncio
async def test_approve_and_send_mock_mode(
    email_service, mock_email_draft_repo, mock_activity_repo, mock_lead_repo
):
    lead_id = uuid.uuid4()
    draft = _make_draft(lead_id=lead_id)
    approved_draft = _make_draft(lead_id=lead_id, approved=True)
    sent_draft = _make_draft(
        lead_id=lead_id,
        approved=True,
        delivery_status=DeliveryStatus.SENT.value,
    )
    lead = _make_lead(lead_id=lead_id)

    mock_email_draft_repo.get_by_id.return_value = draft
    mock_email_draft_repo.update.side_effect = [approved_draft, sent_draft]
    mock_lead_repo.get_by_id.return_value = lead

    with patch("app.services.email_service.settings") as mock_settings:
        mock_settings.EMAIL_MODE = "mock"
        result = await email_service.approve_and_send(draft.id)

    assert mock_email_draft_repo.update.call_count == 2

    # First call: approve
    first_call_kwargs = mock_email_draft_repo.update.call_args_list[0].kwargs
    assert first_call_kwargs["approved"] is True

    # Second call: set sent
    second_call_kwargs = mock_email_draft_repo.update.call_args_list[1].kwargs
    assert second_call_kwargs["delivery_status"] == DeliveryStatus.SENT.value

    # Activity logged for EMAIL_SENT
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["type"] == ActivityType.EMAIL_SENT.value
    assert activity_kwargs["payload"]["mode"] == "mock"

    # Lead status updated to CONTACTED
    mock_lead_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_approve_and_send_draft_not_found(email_service, mock_email_draft_repo):
    mock_email_draft_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Email draft .* not found"):
        await email_service.approve_and_send(uuid.uuid4())


@pytest.mark.asyncio
async def test_approve_and_send_smtp_mode_fails(
    email_service, mock_email_draft_repo, mock_activity_repo
):
    draft = _make_draft()
    mock_email_draft_repo.get_by_id.return_value = draft
    mock_email_draft_repo.update.return_value = draft

    with patch("app.services.email_service.settings") as mock_settings:
        mock_settings.EMAIL_MODE = "smtp"
        result = await email_service.approve_and_send(draft.id)

    # Second update should set FAILED status
    last_call_kwargs = mock_email_draft_repo.update.call_args_list[-1].kwargs
    assert last_call_kwargs["delivery_status"] == DeliveryStatus.FAILED.value
    assert "not implemented" in last_call_kwargs["error_message"]


@pytest.mark.asyncio
async def test_approve_and_send_unknown_mode(
    email_service, mock_email_draft_repo, mock_activity_repo
):
    draft = _make_draft()
    mock_email_draft_repo.get_by_id.return_value = draft
    mock_email_draft_repo.update.return_value = draft

    with patch("app.services.email_service.settings") as mock_settings:
        mock_settings.EMAIL_MODE = "carrier_pigeon"
        result = await email_service.approve_and_send(draft.id)

    last_call_kwargs = mock_email_draft_repo.update.call_args_list[-1].kwargs
    assert last_call_kwargs["delivery_status"] == DeliveryStatus.FAILED.value
    assert "carrier_pigeon" in last_call_kwargs["error_message"]
