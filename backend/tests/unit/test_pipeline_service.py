"""Test pipeline service — graph invocation, state building, result handling, error paths."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ActivityType, PipelineRunStatus, ProcessingStatus
from app.models.orm import Lead, PipelineRun
from app.services.pipeline_service import PipelineService


# --- Fixtures ---


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_lead_repo():
    return AsyncMock()


@pytest.fixture
def mock_pipeline_run_repo():
    return AsyncMock()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock()


@pytest.fixture
def mock_email_draft_repo():
    return AsyncMock()


@pytest.fixture
def mock_trace_repo():
    return AsyncMock()


@pytest.fixture
def pipeline_service(
    mock_session,
    mock_lead_repo,
    mock_pipeline_run_repo,
    mock_activity_repo,
    mock_email_draft_repo,
    mock_trace_repo,
):
    service = PipelineService(mock_session)
    service.lead_repo = mock_lead_repo
    service.pipeline_run_repo = mock_pipeline_run_repo
    service.activity_repo = mock_activity_repo
    service.email_draft_repo = mock_email_draft_repo
    service.trace_repo = mock_trace_repo
    return service


def _make_lead(lead_id=None):
    return Lead(
        id=lead_id or uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email="jane@acme.com",
        phone="+1-555-0123",
        company_name="Acme Corp",
        job_title="VP Engineering",
        industry="SaaS",
        company_size="100-500",
        country="USA",
        source="web_form",
        budget_range="$50k-$100k",
        pain_point="Need automation",
        urgency="high",
        lead_message="Looking for a solution",
        status="NEW",
        processing_status="IDLE",
    )


def _make_pipeline_run(lead_id=None):
    return PipelineRun(
        id=uuid.uuid4(),
        lead_id=lead_id or uuid.uuid4(),
        thread_id="test-thread",
        status=PipelineRunStatus.RUNNING.value,
    )


def _make_graph_result(include_email=True, include_enrichment=True, include_score=True):
    """Build a typical successful graph result dict."""
    result = {
        "lead_id": str(uuid.uuid4()),
        "lead": {},
        "errors": [],
        "node_events": {"normalize": {"duration_ms": 5}, "score": {"duration_ms": 120}},
        "llm_inputs": {"score_prompt": "Score this lead jane@acme.com"},
        "llm_outputs": {"score_response": {"score_value": 85}},
        "node_timings": {"normalize": 0.005, "enrich": 0.01, "score": 0.12},
    }
    if include_enrichment:
        result["enrichment"] = {"company_domain": "acme.com", "is_corporate_email": True}
    if include_score:
        result["score"] = {"score_value": 85, "score_label": "HOT", "rationale": "Strong fit"}
        result["decision"] = {"action": "SEND_EMAIL", "reasoning": "Hot lead, ready for outreach"}
    if include_email:
        result["email_draft"] = {
            "subject": "Solving Automation at Acme Corp",
            "body": "Hi Jane, ...",
            "variant": "first_touch",
        }
    return result


# --- _build_initial_state ---


def test_build_initial_state(pipeline_service):
    lead = _make_lead()
    state = pipeline_service._build_initial_state(lead)

    assert state["lead_id"] == str(lead.id)
    assert state["lead"]["first_name"] == "Jane"
    assert state["lead"]["last_name"] == "Smith"
    assert state["lead"]["email"] == "jane@acme.com"
    assert state["lead"]["company_name"] == "Acme Corp"
    assert state["enrichment"] == {}
    assert state["score"] is None
    assert state["decision"] is None
    assert state["email_draft"] is None
    assert state["errors"] == []


def test_build_initial_state_replaces_none_with_empty_string(pipeline_service):
    lead = _make_lead()
    lead.phone = None
    lead.industry = None
    lead.job_title = None

    state = pipeline_service._build_initial_state(lead)

    assert state["lead"]["phone"] == ""
    assert state["lead"]["industry"] == ""
    assert state["lead"]["job_title"] == ""


# --- _update_lead_from_result ---


@pytest.mark.asyncio
async def test_update_lead_from_result_full(pipeline_service, mock_lead_repo):
    lead = _make_lead()
    result = _make_graph_result()

    await pipeline_service._update_lead_from_result(lead, result)

    mock_lead_repo.update.assert_called_once()
    kwargs = mock_lead_repo.update.call_args.kwargs
    assert kwargs["score_value"] == 85
    assert kwargs["score_label"] == "HOT"
    assert kwargs["score_rationale"] == "Strong fit"
    assert kwargs["recommended_action"] == "SEND_EMAIL"
    assert kwargs["enrichment_data"]["company_domain"] == "acme.com"


@pytest.mark.asyncio
async def test_update_lead_from_result_no_score(pipeline_service, mock_lead_repo):
    lead = _make_lead()
    result = _make_graph_result(include_score=False, include_email=False)

    await pipeline_service._update_lead_from_result(lead, result)

    mock_lead_repo.update.assert_called_once()
    kwargs = mock_lead_repo.update.call_args.kwargs
    # Only enrichment should be present
    assert "enrichment_data" in kwargs
    assert "score_value" not in kwargs
    assert "recommended_action" not in kwargs


@pytest.mark.asyncio
async def test_update_lead_from_result_empty(pipeline_service, mock_lead_repo):
    lead = _make_lead()
    result = _make_graph_result(
        include_score=False, include_email=False, include_enrichment=False
    )

    await pipeline_service._update_lead_from_result(lead, result)

    # No update_data → update should not be called
    mock_lead_repo.update.assert_not_called()


# --- _log_pipeline_activities ---


@pytest.mark.asyncio
async def test_log_pipeline_activities_all_steps(pipeline_service, mock_activity_repo):
    lead_id = uuid.uuid4()
    result = _make_graph_result()

    await pipeline_service._log_pipeline_activities(lead_id, result)

    # Should log ENRICHED, SCORED, and EMAIL_DRAFTED
    assert mock_activity_repo.create.call_count == 3
    activity_types = [
        call.kwargs["type"] for call in mock_activity_repo.create.call_args_list
    ]
    assert ActivityType.ENRICHED.value in activity_types
    assert ActivityType.SCORED.value in activity_types
    assert ActivityType.EMAIL_DRAFTED.value in activity_types


@pytest.mark.asyncio
async def test_log_pipeline_activities_no_email(pipeline_service, mock_activity_repo):
    lead_id = uuid.uuid4()
    result = _make_graph_result(include_email=False)

    await pipeline_service._log_pipeline_activities(lead_id, result)

    # ENRICHED + SCORED only
    assert mock_activity_repo.create.call_count == 2


@pytest.mark.asyncio
async def test_log_pipeline_activities_score_only(pipeline_service, mock_activity_repo):
    lead_id = uuid.uuid4()
    result = _make_graph_result(include_email=False, include_enrichment=False)

    await pipeline_service._log_pipeline_activities(lead_id, result)

    assert mock_activity_repo.create.call_count == 1
    assert mock_activity_repo.create.call_args.kwargs["type"] == ActivityType.SCORED.value


# --- _create_email_draft_from_result ---


@pytest.mark.asyncio
async def test_create_email_draft_from_result(pipeline_service, mock_email_draft_repo):
    lead_id = uuid.uuid4()
    draft_data = {
        "subject": "Test Subject",
        "body": "Test body",
        "variant": "first_touch",
    }

    await pipeline_service._create_email_draft_from_result(lead_id, draft_data)

    mock_email_draft_repo.create.assert_called_once()
    kwargs = mock_email_draft_repo.create.call_args.kwargs
    assert kwargs["lead_id"] == lead_id
    assert kwargs["subject"] == "Test Subject"
    assert kwargs["body"] == "Test body"
    assert kwargs["variant"] == "first_touch"


@pytest.mark.asyncio
async def test_create_email_draft_defaults_missing_fields(pipeline_service, mock_email_draft_repo):
    lead_id = uuid.uuid4()
    # Sparse draft data — missing subject/body/variant
    await pipeline_service._create_email_draft_from_result(lead_id, {})

    kwargs = mock_email_draft_repo.create.call_args.kwargs
    assert kwargs["subject"] == ""
    assert kwargs["body"] == ""
    assert kwargs["variant"] == "first_touch"


# --- _create_trace ---


@pytest.mark.asyncio
async def test_create_trace_delegates_to_trace_service(pipeline_service, mock_session):
    lead_id = uuid.uuid4()
    result = _make_graph_result()

    mock_trace_service = MagicMock()
    mock_trace_service.create_trace = AsyncMock()

    with patch(
        "app.services.trace_service.TraceService",
        return_value=mock_trace_service,
    ):
        await pipeline_service._create_trace(lead_id, "thread-123", result)

    mock_trace_service.create_trace.assert_called_once()
    kwargs = mock_trace_service.create_trace.call_args.kwargs
    assert kwargs["lead_id"] == lead_id
    assert kwargs["graph_run_id"] == "thread-123"
    assert kwargs["node_events"] == result["node_events"]
    assert kwargs["llm_inputs"] == result["llm_inputs"]
    assert kwargs["llm_outputs"] == result["llm_outputs"]


# --- run_pipeline (success path) ---


@pytest.mark.asyncio
async def test_run_pipeline_success(
    pipeline_service,
    mock_lead_repo,
    mock_pipeline_run_repo,
    mock_activity_repo,
    mock_email_draft_repo,
):
    lead = _make_lead()
    lead_id = lead.id
    mock_lead_repo.get_by_id.return_value = lead

    pipeline_run = _make_pipeline_run(lead_id=lead_id)
    mock_pipeline_run_repo.create.return_value = pipeline_run

    graph_result = _make_graph_result()

    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = graph_result

    mock_trace_service = MagicMock()
    mock_trace_service.create_trace = AsyncMock()

    with patch(
        "app.graphs.lead_pipeline.get_graph", return_value=mock_graph
    ), patch(
        "app.services.trace_service.TraceService",
        return_value=mock_trace_service,
    ):
        result = await pipeline_service.run_pipeline(lead_id)

    # Returns pipeline_run
    assert result == pipeline_run

    # PipelineRun created with RUNNING status
    create_kwargs = mock_pipeline_run_repo.create.call_args.kwargs
    assert create_kwargs["lead_id"] == lead_id
    assert create_kwargs["status"] == PipelineRunStatus.RUNNING.value

    # Lead set to PROCESSING then back to IDLE
    lead_update_calls = mock_lead_repo.update.call_args_list
    # First call: PROCESSING
    assert lead_update_calls[0].kwargs["processing_status"] == ProcessingStatus.PROCESSING.value
    # Second call: update from result (score, enrichment, etc.)
    assert "score_value" in lead_update_calls[1].kwargs
    # Third call: back to IDLE
    assert lead_update_calls[2].kwargs["processing_status"] == ProcessingStatus.IDLE.value

    # Graph was invoked with correct initial state
    mock_graph.ainvoke.assert_called_once()
    invoke_args = mock_graph.ainvoke.call_args
    initial_state = invoke_args[0][0]
    assert initial_state["lead"]["first_name"] == "Jane"
    assert initial_state["lead"]["email"] == "jane@acme.com"

    # PipelineRun updated to COMPLETED
    final_update = mock_pipeline_run_repo.update.call_args
    assert final_update.kwargs["status"] == PipelineRunStatus.COMPLETED.value
    assert final_update.kwargs["node_timings"] == graph_result["node_timings"]

    # Email draft created
    mock_email_draft_repo.create.assert_called_once()

    # Activities logged (ENRICHED + SCORED + EMAIL_DRAFTED)
    assert mock_activity_repo.create.call_count == 3

    # Trace created
    mock_trace_service.create_trace.assert_called_once()


@pytest.mark.asyncio
async def test_run_pipeline_no_email_draft(
    pipeline_service,
    mock_lead_repo,
    mock_pipeline_run_repo,
    mock_email_draft_repo,
):
    lead = _make_lead()
    mock_lead_repo.get_by_id.return_value = lead
    mock_pipeline_run_repo.create.return_value = _make_pipeline_run(lead_id=lead.id)

    graph_result = _make_graph_result(include_email=False)
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = graph_result

    mock_trace_service = MagicMock()
    mock_trace_service.create_trace = AsyncMock()

    with patch(
        "app.graphs.lead_pipeline.get_graph", return_value=mock_graph
    ), patch(
        "app.services.trace_service.TraceService",
        return_value=mock_trace_service,
    ):
        await pipeline_service.run_pipeline(lead.id)

    # Email draft should NOT be created
    mock_email_draft_repo.create.assert_not_called()


# --- run_pipeline (failure path) ---


@pytest.mark.asyncio
async def test_run_pipeline_lead_not_found(pipeline_service, mock_lead_repo):
    mock_lead_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="Lead .* not found"):
        await pipeline_service.run_pipeline(uuid.uuid4())


@pytest.mark.asyncio
async def test_run_pipeline_graph_failure(
    pipeline_service,
    mock_lead_repo,
    mock_pipeline_run_repo,
    mock_activity_repo,
):
    lead = _make_lead()
    lead_id = lead.id
    mock_lead_repo.get_by_id.return_value = lead

    pipeline_run = _make_pipeline_run(lead_id=lead_id)
    mock_pipeline_run_repo.create.return_value = pipeline_run

    mock_graph = AsyncMock()
    mock_graph.ainvoke.side_effect = RuntimeError("Graph node exploded")

    with patch("app.graphs.lead_pipeline.get_graph", return_value=mock_graph):
        with pytest.raises(RuntimeError, match="Graph node exploded"):
            await pipeline_service.run_pipeline(lead_id)

    # PipelineRun updated to FAILED
    update_kwargs = mock_pipeline_run_repo.update.call_args.kwargs
    assert update_kwargs["status"] == PipelineRunStatus.FAILED.value
    assert "Graph node exploded" in update_kwargs["error_message"]

    # Lead set to FAILED processing status
    last_lead_update = mock_lead_repo.update.call_args_list[-1]
    assert last_lead_update.kwargs["processing_status"] == ProcessingStatus.FAILED.value

    # Error activity logged
    mock_activity_repo.create.assert_called_once()
    error_kwargs = mock_activity_repo.create.call_args.kwargs
    assert error_kwargs["type"] == ActivityType.ERROR.value
    assert "Graph node exploded" in error_kwargs["payload"]["error"]
