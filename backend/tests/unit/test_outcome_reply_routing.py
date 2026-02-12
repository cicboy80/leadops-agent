"""Test OutcomeService.handle_inbound_reply() — routing logic after classification."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ActivityType, OutcomeStage, ReplyClassification
from app.models.orm import Lead, LeadOutcomeStage, ReplyClassificationRecord
from app.services.outcome_service import OutcomeService


# --- Fixtures ---


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_stage_repo():
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock()


@pytest.fixture
def outcome_service(mock_session, mock_stage_repo, mock_activity_repo):
    service = OutcomeService(mock_session)
    service.stage_repo = mock_stage_repo
    service.activity_repo = mock_activity_repo
    return service


def _make_lead(lead_id=None, current_stage="EMAIL_SENT"):
    return Lead(
        id=lead_id or uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email="jane@acme.com",
        company_name="Acme Corp",
        industry="SaaS",
        status="QUALIFIED",
        processing_status="IDLE",
        current_outcome_stage=current_stage,
    )


def _make_classification_record(lead_id, classification, confidence=0.85):
    return ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=lead_id,
        reply_body="test reply",
        classification=classification,
        confidence=confidence,
        reasoning="test reasoning",
        is_auto_reply=(classification == ReplyClassification.OUT_OF_OFFICE.value),
        extracted_dates=[],
    )


def _make_stage_record(lead_id, stage):
    return LeadOutcomeStage(
        id=uuid.uuid4(),
        lead_id=lead_id,
        stage=stage,
        reason="AUTOMATIC",
        triggered_by="reply_agent",
    )


def _patch_dependencies(classification_value, lead):
    """Return context managers that patch ReplyClassificationService, NotificationService, and CalendarService."""
    classification_record = _make_classification_record(
        lead.id, classification_value
    )

    mock_classification_service = MagicMock()
    mock_classification_service.classify_reply = AsyncMock(return_value=classification_record)

    mock_notification_service = MagicMock()
    mock_notification_service.notify_reply_classified = AsyncMock()
    mock_notification_service.notify_demo_requested = AsyncMock()

    mock_calendar_service = MagicMock()
    mock_calendar_service.get_booking_link = AsyncMock(return_value="https://calendly.com/test")

    patches = [
        patch(
            "app.services.reply_classification_service.ReplyClassificationService",
            return_value=mock_classification_service,
        ),
        patch(
            "app.services.notification_service.NotificationService",
            return_value=mock_notification_service,
        ),
        patch(
            "app.services.calendar_service.CalendarService",
            return_value=mock_calendar_service,
        ),
    ]

    return patches, mock_notification_service, mock_calendar_service


# --- Reply routing tests ---


@pytest.mark.asyncio
async def test_reply_out_of_office_no_transition(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead

    patches, mock_notif, _ = _patch_dependencies(
        ReplyClassification.OUT_OF_OFFICE.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="I am out of office until March 5.",
            sender_email="jane@acme.com",
        )

    assert result["classification"] == ReplyClassification.OUT_OF_OFFICE.value
    assert result["stage_record"] is None
    assert "out-of-office" in result["auto_action_taken"]
    mock_stage_repo.transition_to_stage.assert_not_called()
    mock_notif.notify_reply_classified.assert_called_once()


@pytest.mark.asyncio
async def test_reply_unsubscribe_auto_disqualifies(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.DISQUALIFIED.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, mock_notif, _ = _patch_dependencies(
        ReplyClassification.UNSUBSCRIBE.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="Please remove me from your mailing list",
        )

    assert result["classification"] == ReplyClassification.UNSUBSCRIBE.value
    assert result["stage_record"] is not None
    assert result["stage_record"].stage == OutcomeStage.DISQUALIFIED.value
    mock_stage_repo.transition_to_stage.assert_called_once()
    call_kwargs = mock_stage_repo.transition_to_stage.call_args.kwargs
    assert call_kwargs["new_stage"] == OutcomeStage.DISQUALIFIED.value


@pytest.mark.asyncio
async def test_reply_not_interested_auto_closes(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.CLOSED_LOST.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, mock_notif, _ = _patch_dependencies(
        ReplyClassification.NOT_INTERESTED.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="No thanks, not interested at this time",
        )

    assert result["classification"] == ReplyClassification.NOT_INTERESTED.value
    assert result["stage_record"].stage == OutcomeStage.CLOSED_LOST.value
    call_kwargs = mock_stage_repo.transition_to_stage.call_args.kwargs
    assert call_kwargs["new_stage"] == OutcomeStage.CLOSED_LOST.value


@pytest.mark.asyncio
async def test_reply_interested_transitions_to_responded(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.RESPONDED.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, _, mock_calendar = _patch_dependencies(
        ReplyClassification.INTERESTED_BOOK_DEMO.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="I'd love to schedule a demo next week!",
        )

    assert result["classification"] == ReplyClassification.INTERESTED_BOOK_DEMO.value
    assert result["stage_record"].stage == OutcomeStage.RESPONDED.value
    mock_calendar.get_booking_link.assert_called_once_with(lead.id)


@pytest.mark.asyncio
async def test_reply_question_transitions_to_responded(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.RESPONDED.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, mock_notif, _ = _patch_dependencies(
        ReplyClassification.QUESTION.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="Can you tell me more about your pricing?",
        )

    assert result["classification"] == ReplyClassification.QUESTION.value
    assert result["stage_record"].stage == OutcomeStage.RESPONDED.value
    mock_notif.notify_reply_classified.assert_called_once()


@pytest.mark.asyncio
async def test_reply_unclear_transitions_to_responded(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.RESPONDED.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, mock_notif, _ = _patch_dependencies(
        ReplyClassification.UNCLEAR.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="Lorem ipsum dolor sit amet",
        )

    assert result["classification"] == ReplyClassification.UNCLEAR.value
    assert result["stage_record"].stage == OutcomeStage.RESPONDED.value


@pytest.mark.asyncio
async def test_reply_lead_not_found(outcome_service, mock_session):
    mock_session.get.return_value = None

    with pytest.raises(ValueError, match="Lead .* not found"):
        await outcome_service.handle_inbound_reply(
            lead_id=uuid.uuid4(),
            reply_body="Hello!",
        )


@pytest.mark.asyncio
async def test_reply_returns_classification_details(
    outcome_service, mock_session, mock_stage_repo, mock_activity_repo
):
    lead = _make_lead()
    mock_session.get.return_value = lead
    stage_record = _make_stage_record(lead.id, OutcomeStage.RESPONDED.value)
    mock_stage_repo.transition_to_stage.return_value = stage_record

    patches, _, _ = _patch_dependencies(
        ReplyClassification.QUESTION.value, lead
    )

    with patches[0], patches[1], patches[2]:
        result = await outcome_service.handle_inbound_reply(
            lead_id=lead.id,
            reply_body="What integrations do you support?",
        )

    # Verify return dict structure
    assert "classification" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert "extracted_dates" in result
    assert "auto_action_taken" in result
    assert "stage_record" in result
    assert isinstance(result["extracted_dates"], list)
