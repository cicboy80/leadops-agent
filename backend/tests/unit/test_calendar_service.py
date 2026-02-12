"""Test calendar service — booking links, webhook handling, signature verification."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ActivityType, OutcomeStage
from app.models.orm import Lead, LeadOutcomeStage
from app.services.calendar_service import (
    CalendarService,
    MockCalendarProvider,
    _get_provider,
)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock()


@pytest.fixture
def mock_stage_repo():
    return AsyncMock()


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.get_scheduling_link.return_value = "https://calendly.com/test/30min"
    return provider


@pytest.fixture
def calendar_service(mock_session, mock_activity_repo, mock_stage_repo, mock_provider):
    service = CalendarService(mock_session)
    service.activity_repo = mock_activity_repo
    service.stage_repo = mock_stage_repo
    service.provider = mock_provider
    return service


def _make_lead(lead_id=None, current_stage="EMAIL_SENT", email="jane@acme.com"):
    return Lead(
        id=lead_id or uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email=email,
        company_name="Acme Corp",
        status="QUALIFIED",
        processing_status="IDLE",
        current_outcome_stage=current_stage,
    )


# --- get_booking_link ---


@pytest.mark.asyncio
async def test_get_booking_link(calendar_service, mock_provider, mock_activity_repo):
    lead_id = uuid.uuid4()

    link = await calendar_service.get_booking_link(lead_id)

    assert link == "https://calendly.com/test/30min"
    mock_provider.get_scheduling_link.assert_called_once()

    # Activity logged
    mock_activity_repo.create.assert_called_once()
    kwargs = mock_activity_repo.create.call_args.kwargs
    assert kwargs["lead_id"] == lead_id
    assert kwargs["type"] == ActivityType.CALENDLY_LINK_SENT.value
    assert kwargs["payload"]["scheduling_link"] == link


# --- MockCalendarProvider ---


@pytest.mark.asyncio
async def test_mock_provider_scheduling_link():
    provider = MockCalendarProvider()
    link = await provider.get_scheduling_link()
    assert "calendly.com" in link


@pytest.mark.asyncio
async def test_mock_provider_availability():
    provider = MockCalendarProvider()
    slots = await provider.check_availability({})
    assert len(slots) > 0
    assert "slots" in slots[0]


@pytest.mark.asyncio
async def test_mock_provider_get_event():
    provider = MockCalendarProvider()
    event = await provider.get_event("evt-123")
    assert event["id"] == "evt-123"


# --- _get_provider ---


def test_get_provider_mock_when_no_key():
    with patch("app.services.calendar_service.settings") as mock_settings:
        mock_settings.CALENDLY_API_KEY = ""
        provider = _get_provider()
    assert isinstance(provider, MockCalendarProvider)


# --- handle_booking_webhook ---


@pytest.mark.asyncio
async def test_webhook_books_demo_from_email_sent(
    calendar_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead(current_stage=OutcomeStage.EMAIL_SENT.value, email="jane@acme.com")

    # Mock session.execute for the SELECT query
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = lead
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    mock_stage_repo.transition_to_stage.return_value = LeadOutcomeStage(
        id=uuid.uuid4(), lead_id=lead.id, stage=OutcomeStage.BOOKED_DEMO.value,
        reason="AUTOMATIC", triggered_by="calendly_webhook",
    )

    result = await calendar_service.handle_booking_webhook({
        "payload": {
            "email": "jane@acme.com",
            "event": "https://api.calendly.com/events/abc123",
        }
    })

    assert result["status"] == "booked"
    # Should transition through RESPONDED then BOOKED_DEMO (2 calls)
    assert mock_stage_repo.transition_to_stage.call_count == 2

    first_transition = mock_stage_repo.transition_to_stage.call_args_list[0].kwargs
    assert first_transition["new_stage"] == OutcomeStage.RESPONDED.value

    second_transition = mock_stage_repo.transition_to_stage.call_args_list[1].kwargs
    assert second_transition["new_stage"] == OutcomeStage.BOOKED_DEMO.value

    # DEMO_BOOKED activity logged
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["type"] == ActivityType.DEMO_BOOKED.value


@pytest.mark.asyncio
async def test_webhook_books_demo_from_responded(
    calendar_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead(current_stage=OutcomeStage.RESPONDED.value, email="jane@acme.com")

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = lead
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    mock_stage_repo.transition_to_stage.return_value = LeadOutcomeStage(
        id=uuid.uuid4(), lead_id=lead.id, stage=OutcomeStage.BOOKED_DEMO.value,
        reason="AUTOMATIC", triggered_by="calendly_webhook",
    )

    result = await calendar_service.handle_booking_webhook({
        "payload": {"email": "jane@acme.com", "event": "evt-456"}
    })

    assert result["status"] == "booked"
    # Should go directly to BOOKED_DEMO (1 call, no intermediate RESPONDED)
    assert mock_stage_repo.transition_to_stage.call_count == 1
    kwargs = mock_stage_repo.transition_to_stage.call_args.kwargs
    assert kwargs["new_stage"] == OutcomeStage.BOOKED_DEMO.value


@pytest.mark.asyncio
async def test_webhook_no_email_ignored(calendar_service, mock_session):
    result = await calendar_service.handle_booking_webhook({
        "payload": {"event": "evt-789"}
    })

    assert result["status"] == "ignored"
    assert result["reason"] == "no email"


@pytest.mark.asyncio
async def test_webhook_no_matching_lead(calendar_service, mock_session):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await calendar_service.handle_booking_webhook({
        "payload": {"email": "unknown@example.com", "event": "evt-000"}
    })

    assert result["status"] == "ignored"
    assert result["reason"] == "no matching lead"


@pytest.mark.asyncio
async def test_webhook_lead_not_in_bookable_stage(calendar_service, mock_session):
    lead = _make_lead(current_stage=OutcomeStage.DISQUALIFIED.value, email="jane@acme.com")

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = lead
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await calendar_service.handle_booking_webhook({
        "payload": {"email": "jane@acme.com", "event": "evt-999"}
    })

    assert result["status"] == "ignored"
    assert "DISQUALIFIED" in result["reason"]


# --- verify_webhook_signature ---


def test_verify_signature_no_secret_configured():
    with patch("app.services.calendar_service.settings") as mock_settings:
        mock_settings.CALENDLY_WEBHOOK_SECRET = ""
        assert CalendarService.verify_webhook_signature(b"payload", "any-sig") is True


def test_verify_signature_valid():
    import hashlib
    import hmac

    secret = "test-secret"
    payload = b'{"event": "invitee.created"}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch("app.services.calendar_service.settings") as mock_settings:
        mock_settings.CALENDLY_WEBHOOK_SECRET = secret
        assert CalendarService.verify_webhook_signature(payload, expected) is True


def test_verify_signature_invalid():
    with patch("app.services.calendar_service.settings") as mock_settings:
        mock_settings.CALENDLY_WEBHOOK_SECRET = "real-secret"
        assert CalendarService.verify_webhook_signature(b"payload", "wrong-sig") is False
