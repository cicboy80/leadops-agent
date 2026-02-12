"""Test trace service — PII redaction and trace creation."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.orm import Trace
from app.services.trace_service import TraceService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_trace_repo():
    return AsyncMock()


@pytest.fixture
def trace_service(mock_session, mock_trace_repo):
    service = TraceService(mock_session)
    service.trace_repo = mock_trace_repo
    return service


# --- PII redaction ---


def test_redact_pii_simple_email():
    service = TraceService(AsyncMock())
    data = {"prompt": "Contact john@example.com for details"}
    result = service._redact_pii(data)

    assert "john@example.com" not in result["prompt"]
    assert "REDACTED_" in result["prompt"]


def test_redact_pii_nested_dict():
    service = TraceService(AsyncMock())
    data = {
        "outer": {
            "inner": "Send to jane.doe@company.io please"
        }
    }
    result = service._redact_pii(data)

    assert "jane.doe@company.io" not in result["outer"]["inner"]
    assert "REDACTED_" in result["outer"]["inner"]


def test_redact_pii_list_values():
    service = TraceService(AsyncMock())
    data = {
        "emails": ["alice@test.com", "bob@test.com"]
    }
    result = service._redact_pii(data)

    assert "alice@test.com" not in result["emails"][0]
    assert "bob@test.com" not in result["emails"][1]
    assert all("REDACTED_" in item for item in result["emails"])


def test_redact_pii_preserves_non_email():
    service = TraceService(AsyncMock())
    data = {"name": "John Doe", "count": 42, "flag": True}
    result = service._redact_pii(data)

    assert result["name"] == "John Doe"
    assert result["count"] == 42
    assert result["flag"] is True


def test_redact_pii_multiple_emails_in_string():
    service = TraceService(AsyncMock())
    data = {"text": "CC: a@b.com and c@d.com"}
    result = service._redact_pii(data)

    assert "a@b.com" not in result["text"]
    assert "c@d.com" not in result["text"]


def test_redact_pii_string_returns_unchanged_for_none():
    service = TraceService(AsyncMock())
    assert service._redact_pii_string(None) is None


def test_redact_pii_empty_dict():
    service = TraceService(AsyncMock())
    assert service._redact_pii({}) == {}


# --- hash_email ---


def test_hash_email_deterministic():
    h1 = TraceService.hash_email("test@example.com")
    h2 = TraceService.hash_email("test@example.com")
    assert h1 == h2


def test_hash_email_case_insensitive():
    h1 = TraceService.hash_email("Test@Example.COM")
    h2 = TraceService.hash_email("test@example.com")
    assert h1 == h2


def test_hash_email_different_emails_differ():
    h1 = TraceService.hash_email("a@b.com")
    h2 = TraceService.hash_email("c@d.com")
    assert h1 != h2


# --- create_trace ---


@pytest.mark.asyncio
async def test_create_trace_redacts_llm_inputs(trace_service, mock_trace_repo):
    lead_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    mock_trace_repo.create.return_value = Trace(
        id=trace_id,
        lead_id=lead_id,
        graph_run_id="run-123",
    )

    result = await trace_service.create_trace(
        lead_id=lead_id,
        graph_run_id="run-123",
        node_events={"normalize": {"status": "ok"}},
        llm_inputs={"prompt": "Score lead john@acme.com"},
        llm_outputs={"score": 85},
    )

    mock_trace_repo.create.assert_called_once()
    kwargs = mock_trace_repo.create.call_args.kwargs
    # llm_inputs should be redacted
    assert "john@acme.com" not in str(kwargs["llm_inputs"])
    # llm_outputs should be passed through as-is
    assert kwargs["llm_outputs"] == {"score": 85}
    # node_events passed through
    assert kwargs["node_events"] == {"normalize": {"status": "ok"}}
    assert result.id == trace_id


@pytest.mark.asyncio
async def test_create_trace_no_llm_inputs(trace_service, mock_trace_repo):
    lead_id = uuid.uuid4()
    mock_trace_repo.create.return_value = Trace(
        id=uuid.uuid4(), lead_id=lead_id, graph_run_id="run-456"
    )

    await trace_service.create_trace(
        lead_id=lead_id,
        graph_run_id="run-456",
    )

    kwargs = mock_trace_repo.create.call_args.kwargs
    assert kwargs["llm_inputs"] is None
    assert kwargs["llm_outputs"] is None


# --- get_traces ---


@pytest.mark.asyncio
async def test_get_traces(trace_service, mock_trace_repo):
    lead_id = uuid.uuid4()
    traces = [
        Trace(id=uuid.uuid4(), lead_id=lead_id, graph_run_id="run-1"),
        Trace(id=uuid.uuid4(), lead_id=lead_id, graph_run_id="run-2"),
    ]
    mock_trace_repo.list.return_value = (traces, "cursor-abc")

    result, cursor = await trace_service.get_traces(lead_id=lead_id, limit=10)

    mock_trace_repo.list.assert_called_once_with(
        filters={"lead_id": lead_id}, cursor=None, limit=10
    )
    assert len(result) == 2
    assert cursor == "cursor-abc"
