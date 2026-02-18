"""Test notification service — create, list, mark-read."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.orm import Notification
from app.services.notification_service import NotificationService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_notification_repo():
    return AsyncMock()


@pytest.fixture
def notification_service(mock_session, mock_notification_repo):
    service = NotificationService(mock_session)
    service.repo = mock_notification_repo
    return service


def _make_notification(lead_id=None, **kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        lead_id=lead_id or uuid.uuid4(),
        type="reply_classified",
        title="Reply classified: INTERESTED_BOOK_DEMO",
        body="Lead Jane Smith replied.",
    )
    defaults.update(kwargs)
    return Notification(**defaults)


# --- notify_reply_classified ---


@pytest.mark.asyncio
async def test_notify_reply_classified(notification_service, mock_notification_repo):
    lead_id = uuid.uuid4()
    notif = _make_notification(lead_id=lead_id)
    mock_notification_repo.create.return_value = notif

    result = await notification_service.notify_reply_classified(
        lead_id=lead_id,
        classification="INTERESTED_BOOK_DEMO",
        reply_preview="I'd love to see a demo",
        lead_name="Jane Smith",
    )

    mock_notification_repo.create.assert_called_once()
    kwargs = mock_notification_repo.create.call_args.kwargs
    assert kwargs["lead_id"] == lead_id
    assert kwargs["type"] == "reply_classified"
    assert "INTERESTED_BOOK_DEMO" in kwargs["title"]
    assert kwargs["metadata_json"]["classification"] == "INTERESTED_BOOK_DEMO"
    assert result.id == notif.id


@pytest.mark.asyncio
async def test_notify_reply_classified_truncates_preview(notification_service, mock_notification_repo):
    lead_id = uuid.uuid4()
    mock_notification_repo.create.return_value = _make_notification(lead_id=lead_id)

    long_preview = "x" * 500
    await notification_service.notify_reply_classified(
        lead_id=lead_id,
        classification="UNCLEAR",
        reply_preview=long_preview,
        lead_name="Jane Smith",
    )

    kwargs = mock_notification_repo.create.call_args.kwargs
    # Body should contain truncated preview (200 chars max from reply_preview)
    assert len(kwargs["body"]) < len(long_preview) + 100


# --- notify_demo_requested ---


@pytest.mark.asyncio
async def test_notify_demo_requested_with_dates(notification_service, mock_notification_repo):
    lead_id = uuid.uuid4()
    mock_notification_repo.create.return_value = _make_notification(
        lead_id=lead_id, type="demo_requested"
    )

    result = await notification_service.notify_demo_requested(
        lead_id=lead_id,
        scheduling_link="https://calendly.com/test/30min",
        extracted_dates=["next monday", "feb 20"],
        lead_name="Jane Smith",
    )

    kwargs = mock_notification_repo.create.call_args.kwargs
    assert kwargs["type"] == "demo_requested"
    assert "Demo requested by Jane Smith" in kwargs["title"]
    assert "next monday" in kwargs["body"]
    assert kwargs["metadata_json"]["scheduling_link"] == "https://calendly.com/test/30min"
    assert kwargs["metadata_json"]["priority"] == "high"


@pytest.mark.asyncio
async def test_notify_demo_requested_no_dates(notification_service, mock_notification_repo):
    lead_id = uuid.uuid4()
    mock_notification_repo.create.return_value = _make_notification(lead_id=lead_id)

    await notification_service.notify_demo_requested(
        lead_id=lead_id,
        scheduling_link=None,
        extracted_dates=[],
        lead_name="",
    )

    kwargs = mock_notification_repo.create.call_args.kwargs
    assert kwargs["title"] == "Demo requested"
    assert "Suggested dates" not in kwargs["body"]


# --- get_unread ---


@pytest.mark.asyncio
async def test_get_unread(notification_service, mock_notification_repo):
    notifs = [_make_notification(), _make_notification()]
    mock_notification_repo.get_unread.return_value = notifs

    result = await notification_service.get_unread()

    mock_notification_repo.get_unread.assert_called_once()
    assert len(result) == 2


# --- get_all ---


@pytest.mark.asyncio
async def test_get_all_unread_only(notification_service, mock_notification_repo):
    mock_notification_repo.get_unread.return_value = [_make_notification()]

    result = await notification_service.get_all(unread_only=True)

    mock_notification_repo.get_unread.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_all_includes_read(notification_service, mock_notification_repo):
    notifs = [_make_notification(), _make_notification()]
    mock_notification_repo.list.return_value = (notifs, None)

    result = await notification_service.get_all(unread_only=False)

    mock_notification_repo.list.assert_called_once_with(filters={}, limit=100)
    assert len(result) == 2


# --- mark_read ---


@pytest.mark.asyncio
async def test_mark_read(notification_service, mock_notification_repo):
    notif_id = uuid.uuid4()
    notif = _make_notification()
    mock_notification_repo.mark_read.return_value = notif

    result = await notification_service.mark_read(notif_id)

    mock_notification_repo.mark_read.assert_called_once_with(notif_id)
    assert result == notif


@pytest.mark.asyncio
async def test_mark_all_read(notification_service, mock_notification_repo):
    mock_notification_repo.mark_all_read.return_value = 5

    result = await notification_service.mark_all_read()

    mock_notification_repo.mark_all_read.assert_called_once()
    assert result == 5
