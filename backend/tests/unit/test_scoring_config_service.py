"""Test scoring config service — config CRUD and EMA learning updates."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.orm import ScoringConfig
from app.services.scoring_config_service import (
    EMA_ALPHA,
    NEGATIVE_OUTCOMES,
    POSITIVE_OUTCOMES,
    ScoringConfigService,
)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_config_repo():
    return AsyncMock()


@pytest.fixture
def scoring_service(mock_session, mock_config_repo):
    service = ScoringConfigService(mock_session)
    service.config_repo = mock_config_repo
    return service


def _make_config(weights=None, thresholds=None):
    return ScoringConfig(
        id=uuid.uuid4(),
        weights=weights or {"industry": 0.3, "budget": 0.3, "urgency": 0.2, "company_size": 0.2},
        thresholds=thresholds or {"hot": 70, "warm": 40, "cold": 0},
        updated_by="system",
    )


# --- get_config ---


@pytest.mark.asyncio
async def test_get_config(scoring_service, mock_config_repo):
    config = _make_config()
    mock_config_repo.get_active.return_value = config

    result = await scoring_service.get_config()

    mock_config_repo.get_active.assert_called_once()
    assert result.weights == config.weights


# --- update_config ---


@pytest.mark.asyncio
async def test_update_config_merges_weights(scoring_service, mock_config_repo):
    current = _make_config()
    mock_config_repo.get_active.return_value = current
    new_config = _make_config(weights={"industry": 0.4, "budget": 0.3, "urgency": 0.15, "company_size": 0.15})
    mock_config_repo.create.return_value = new_config

    result = await scoring_service.update_config(
        weights={"industry": 0.4},
        user="admin",
    )

    mock_config_repo.create.assert_called_once()
    kwargs = mock_config_repo.create.call_args.kwargs
    # industry should be updated, others preserved
    assert kwargs["weights"]["industry"] == 0.4
    assert kwargs["weights"]["budget"] == 0.3
    assert kwargs["updated_by"] == "admin"


@pytest.mark.asyncio
async def test_update_config_merges_thresholds(scoring_service, mock_config_repo):
    current = _make_config()
    mock_config_repo.get_active.return_value = current
    mock_config_repo.create.return_value = _make_config(thresholds={"hot": 80, "warm": 40, "cold": 0})

    await scoring_service.update_config(thresholds={"hot": 80})

    kwargs = mock_config_repo.create.call_args.kwargs
    assert kwargs["thresholds"]["hot"] == 80
    assert kwargs["thresholds"]["warm"] == 40  # preserved


@pytest.mark.asyncio
async def test_update_config_no_changes(scoring_service, mock_config_repo):
    current = _make_config()
    mock_config_repo.get_active.return_value = current
    mock_config_repo.create.return_value = current

    await scoring_service.update_config()

    # Should still create a new record (versioned history)
    mock_config_repo.create.assert_called_once()


# --- update_weights_from_feedback (EMA learning) ---


@pytest.mark.asyncio
async def test_feedback_positive_outcome_low_score_increases_weights(scoring_service, mock_config_repo):
    """Positive outcome + low score (false negative) → weights increase."""
    current = _make_config(
        weights={"industry": 0.3, "budget": 0.3, "urgency": 0.2, "company_size": 0.2}
    )
    mock_config_repo.get_active.return_value = current
    mock_config_repo.create.return_value = _make_config()

    result = await scoring_service.update_weights_from_feedback(
        outcome="booked_demo",  # positive
        lead_score=30,  # below warm threshold (40) → false negative
    )

    # update_config should have been called with adjusted weights
    mock_config_repo.create.assert_called_once()
    kwargs = mock_config_repo.create.call_args.kwargs
    # Weights should be normalized to sum to ~1.0
    total = sum(kwargs["weights"].values())
    assert abs(total - 1.0) < 0.01


@pytest.mark.asyncio
async def test_feedback_negative_outcome_high_score_decreases_weights(scoring_service, mock_config_repo):
    """Negative outcome + high score (false positive) → weights decrease."""
    weights = {"industry": 0.3, "budget": 0.3, "urgency": 0.2, "company_size": 0.2}
    current = _make_config(weights=weights)
    mock_config_repo.get_active.return_value = current
    mock_config_repo.create.return_value = _make_config()

    await scoring_service.update_weights_from_feedback(
        outcome="no_response",  # negative
        lead_score=85,  # above hot threshold (70) → false positive
    )

    mock_config_repo.create.assert_called_once()
    kwargs = mock_config_repo.create.call_args.kwargs
    total = sum(kwargs["weights"].values())
    assert abs(total - 1.0) < 0.01


@pytest.mark.asyncio
async def test_feedback_aligned_no_adjustment(scoring_service, mock_config_repo):
    """Positive outcome + high score → no adjustment needed."""
    current = _make_config()
    mock_config_repo.get_active.return_value = current

    result = await scoring_service.update_weights_from_feedback(
        outcome="booked_demo",  # positive
        lead_score=85,  # high score → correctly predicted
    )

    # Should return current config without creating new one
    mock_config_repo.create.assert_not_called()
    assert result == current


@pytest.mark.asyncio
async def test_feedback_irrelevant_outcome_skips(scoring_service, mock_config_repo):
    """Unknown outcome type → no adjustment."""
    current = _make_config()
    mock_config_repo.get_active.return_value = current

    result = await scoring_service.update_weights_from_feedback(
        outcome="some_unknown_outcome",
        lead_score=50,
    )

    mock_config_repo.create.assert_not_called()
    assert result == current


@pytest.mark.asyncio
async def test_feedback_weights_stay_positive(scoring_service, mock_config_repo):
    """Weights should never go below 0.01 after adjustment."""
    # Start with very small weights
    weights = {"a": 0.01, "b": 0.01, "c": 0.49, "d": 0.49}
    current = _make_config(weights=weights)
    mock_config_repo.get_active.return_value = current
    mock_config_repo.create.return_value = _make_config()

    await scoring_service.update_weights_from_feedback(
        outcome="disqualified",  # negative
        lead_score=90,  # high score → false positive → decrease
    )

    kwargs = mock_config_repo.create.call_args.kwargs
    for v in kwargs["weights"].values():
        assert v >= 0.01


# --- Outcome sets ---


def test_positive_outcomes_set():
    assert "booked_demo" in POSITIVE_OUTCOMES
    assert "closed_won" in POSITIVE_OUTCOMES


def test_negative_outcomes_set():
    assert "no_response" in NEGATIVE_OUTCOMES
    assert "closed_lost" in NEGATIVE_OUTCOMES
    assert "disqualified" in NEGATIVE_OUTCOMES
