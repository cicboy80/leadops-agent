"""Test reply classification service — rule-based, LLM, and override logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ActivityType, ReplyClassification
from app.models.llm_schemas import ReplyClassificationResult
from app.models.orm import Lead, ReplyClassificationRecord
from app.services.reply_classification_service import (
    ReplyClassificationService,
    _extract_dates_from_text,
)


# --- Fixtures ---


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_classification_repo():
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock()


@pytest.fixture
def classification_service(mock_session, mock_classification_repo, mock_activity_repo):
    service = ReplyClassificationService(mock_session)
    service.repo = mock_classification_repo
    service.activity_repo = mock_activity_repo
    return service


@pytest.fixture
def mock_lead():
    return Lead(
        id=uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email="jane@acme.com",
        company_name="Acme Corp",
        industry="SaaS",
        status="QUALIFIED",
        processing_status="IDLE",
        current_outcome_stage="EMAIL_SENT",
    )


# --- Rule-based classification tests ---


@pytest.mark.asyncio
async def test_classify_interested_book_demo(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="I'd love to schedule a demo",
        classification=ReplyClassification.INTERESTED_BOOK_DEMO.value,
        confidence=0.75,
        reasoning="Reply contains interest/scheduling language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="I'd love to schedule a demo",
        )

    assert result.classification == ReplyClassification.INTERESTED_BOOK_DEMO.value


@pytest.mark.asyncio
async def test_classify_not_interested(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="No thanks, not interested",
        classification=ReplyClassification.NOT_INTERESTED.value,
        confidence=0.8,
        reasoning="Reply contains not-interested language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="No thanks, not interested",
        )

    assert result.classification == ReplyClassification.NOT_INTERESTED.value


@pytest.mark.asyncio
async def test_classify_question(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="Can you tell me more about pricing?",
        classification=ReplyClassification.QUESTION.value,
        confidence=0.7,
        reasoning="Reply contains question patterns",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="Can you tell me more about pricing?",
        )

    assert result.classification == ReplyClassification.QUESTION.value


@pytest.mark.asyncio
async def test_classify_out_of_office(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    reply = "I am out of office until March 5th. I will respond when I return."
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body=reply,
        classification=ReplyClassification.OUT_OF_OFFICE.value,
        confidence=0.85,
        reasoning="Reply matches out-of-office patterns",
        is_auto_reply=True,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body=reply,
        )

    assert result.classification == ReplyClassification.OUT_OF_OFFICE.value
    # Verify repo.create was called with is_auto_reply=True
    create_kwargs = mock_classification_repo.create.call_args.kwargs
    assert create_kwargs["is_auto_reply"] is True


@pytest.mark.asyncio
async def test_classify_unsubscribe(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="Please remove me from your list",
        classification=ReplyClassification.UNSUBSCRIBE.value,
        confidence=0.9,
        reasoning="Reply contains unsubscribe/opt-out language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="Please remove me from your list",
        )

    assert result.classification == ReplyClassification.UNSUBSCRIBE.value


@pytest.mark.asyncio
async def test_classify_unclear(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="Lorem ipsum dolor sit amet",
        classification=ReplyClassification.UNCLEAR.value,
        confidence=0.5,
        reasoning="Reply does not match any known patterns",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="Lorem ipsum dolor sit amet",
        )

    assert result.classification == ReplyClassification.UNCLEAR.value
    create_kwargs = mock_classification_repo.create.call_args.kwargs
    assert create_kwargs["confidence"] == 0.5


@pytest.mark.asyncio
async def test_classify_stores_record(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="No thanks",
        classification=ReplyClassification.NOT_INTERESTED.value,
        confidence=0.8,
        reasoning="Reply contains not-interested language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="No thanks, not interested",
            sender_email="jane@acme.com",
        )

    mock_classification_repo.create.assert_called_once()
    kwargs = mock_classification_repo.create.call_args.kwargs
    assert kwargs["lead_id"] == mock_lead.id
    assert kwargs["classification"] == ReplyClassification.NOT_INTERESTED.value
    assert kwargs["confidence"] == 0.8


@pytest.mark.asyncio
async def test_classify_logs_activity(
    classification_service, mock_session, mock_classification_repo, mock_activity_repo, mock_lead
):
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="Sounds great, let's chat",
        classification=ReplyClassification.INTERESTED_BOOK_DEMO.value,
        confidence=0.75,
        reasoning="Reply contains interest/scheduling language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="Sounds great, let's chat",
            sender_email="jane@acme.com",
        )

    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["lead_id"] == mock_lead.id
    assert activity_kwargs["type"] == ActivityType.REPLY_CLASSIFIED.value
    assert activity_kwargs["payload"]["classification"] == ReplyClassification.INTERESTED_BOOK_DEMO.value
    assert activity_kwargs["payload"]["sender_email"] == "jane@acme.com"


@pytest.mark.asyncio
async def test_classify_truncates_long_reply(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    long_reply = "x" * 3000
    mock_session.get.return_value = mock_lead
    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body=long_reply[:2000],
        classification=ReplyClassification.UNCLEAR.value,
        confidence=0.5,
        reasoning="Reply does not match any known patterns",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
        await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body=long_reply,
        )

    kwargs = mock_classification_repo.create.call_args.kwargs
    assert len(kwargs["reply_body"]) == 2000


@pytest.mark.asyncio
async def test_classify_lead_not_found(classification_service, mock_session):
    mock_session.get.return_value = None

    with pytest.raises(ValueError, match="Lead .* not found"):
        with patch("app.services.reply_classification_service.has_llm_key", return_value=False):
            await classification_service.classify_reply(
                lead_id=uuid.uuid4(),
                reply_body="Hello",
            )


# --- Date extraction tests ---


def test_extract_dates_day_names():
    dates = _extract_dates_from_text("How about next Monday or Tuesday?")
    assert any("monday" in d for d in dates)


def test_extract_dates_month_format():
    dates = _extract_dates_from_text("I'm available Jan 15 or Feb 3rd")
    assert any("jan 15" in d for d in dates)


def test_extract_dates_numeric():
    dates = _extract_dates_from_text("Let's do 2/15/2025")
    assert any("2/15/2025" in d for d in dates)


# --- Override tests ---


@pytest.mark.asyncio
async def test_override_classification(
    classification_service, mock_classification_repo, mock_activity_repo
):
    classification_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    mock_classification_repo.override.return_value = ReplyClassificationRecord(
        id=classification_id,
        lead_id=lead_id,
        reply_body="Some reply",
        classification=ReplyClassification.NOT_INTERESTED.value,
        confidence=0.8,
        reasoning="Original reasoning",
        is_auto_reply=False,
        overridden_by="admin@example.com",
        overridden_classification=ReplyClassification.QUESTION.value,
    )

    result = await classification_service.override_classification(
        classification_id=classification_id,
        new_classification=ReplyClassification.QUESTION,
        overridden_by="admin@example.com",
    )

    mock_classification_repo.override.assert_called_once_with(
        classification_id=classification_id,
        new_classification=ReplyClassification.QUESTION.value,
        overridden_by="admin@example.com",
    )
    mock_activity_repo.create.assert_called_once()
    activity_kwargs = mock_activity_repo.create.call_args.kwargs
    assert activity_kwargs["type"] == ActivityType.CLASSIFICATION_OVERRIDDEN.value
    assert activity_kwargs["payload"]["new_classification"] == ReplyClassification.QUESTION.value


@pytest.mark.asyncio
async def test_override_not_found(classification_service, mock_classification_repo):
    mock_classification_repo.override.side_effect = ValueError("Classification not found")

    with pytest.raises(ValueError, match="not found"):
        await classification_service.override_classification(
            classification_id=uuid.uuid4(),
            new_classification=ReplyClassification.NOT_INTERESTED,
            overridden_by="admin@example.com",
        )


# --- LLM path tests ---


@pytest.mark.asyncio
async def test_classify_with_llm(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead

    llm_result = ReplyClassificationResult(
        classification=ReplyClassification.INTERESTED_BOOK_DEMO,
        confidence=0.95,
        reasoning="LLM determined high interest",
        extracted_dates=["next tuesday"],
        is_auto_reply=False,
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.ainvoke = AsyncMock(return_value=llm_result)

    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="I'd love to see a demo next Tuesday!",
        classification=ReplyClassification.INTERESTED_BOOK_DEMO.value,
        confidence=0.95,
        reasoning="LLM determined high interest",
        extracted_dates=["next tuesday"],
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=True), \
         patch("app.services.reply_classification_service.get_llm", return_value=mock_llm):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="I'd love to see a demo next Tuesday!",
        )

    assert result.classification == ReplyClassification.INTERESTED_BOOK_DEMO.value
    assert result.confidence == 0.95
    mock_structured.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_classify_llm_fallback_to_rules(
    classification_service, mock_session, mock_classification_repo, mock_lead
):
    mock_session.get.return_value = mock_lead

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    mock_classification_repo.create.return_value = ReplyClassificationRecord(
        id=uuid.uuid4(),
        lead_id=mock_lead.id,
        reply_body="No thanks, not interested",
        classification=ReplyClassification.NOT_INTERESTED.value,
        confidence=0.8,
        reasoning="Reply contains not-interested language",
        is_auto_reply=False,
    )

    with patch("app.services.reply_classification_service.has_llm_key", return_value=True), \
         patch("app.services.reply_classification_service.get_llm", return_value=mock_llm):
        result = await classification_service.classify_reply(
            lead_id=mock_lead.id,
            reply_body="No thanks, not interested",
        )

    # Should fall back to rule-based and still work
    assert result.classification == ReplyClassification.NOT_INTERESTED.value
    # Verify repo.create was called with rule-based confidence (0.8)
    kwargs = mock_classification_repo.create.call_args.kwargs
    assert kwargs["confidence"] == 0.8
