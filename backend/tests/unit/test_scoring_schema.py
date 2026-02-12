"""Test ScoreResult Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.models.enums import ScoreLabel
from app.models.llm_schemas import ScoreResult


def test_valid_score():
    """Test valid score result."""
    score = ScoreResult(
        score_value=75,
        score_label=ScoreLabel.HOT,
        rationale="This is a valid rationale with enough detail.",
    )

    assert score.score_value == 75
    assert score.score_label == ScoreLabel.HOT
    assert len(score.rationale) >= 10


def test_score_value_in_range():
    """Test score value within valid range (0-100)."""
    # Test minimum
    score_min = ScoreResult(
        score_value=0,
        score_label=ScoreLabel.COLD,
        rationale="Minimum score test rationale.",
    )
    assert score_min.score_value == 0

    # Test maximum
    score_max = ScoreResult(
        score_value=100,
        score_label=ScoreLabel.HOT,
        rationale="Maximum score test rationale.",
    )
    assert score_max.score_value == 100


def test_score_out_of_range_high():
    """Test score value > 100 raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ScoreResult(
            score_value=101,
            score_label=ScoreLabel.HOT,
            rationale="This score is too high.",
        )

    assert "score_value" in str(exc_info.value)


def test_score_out_of_range_low():
    """Test score value < 0 raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ScoreResult(
            score_value=-1,
            score_label=ScoreLabel.COLD,
            rationale="This score is too low.",
        )

    assert "score_value" in str(exc_info.value)


def test_score_invalid_label():
    """Test invalid score label raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ScoreResult(
            score_value=50,
            score_label="INVALID_LABEL",  # type: ignore
            rationale="This has an invalid label.",
        )

    assert "score_label" in str(exc_info.value)


def test_score_short_rationale():
    """Test rationale too short raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ScoreResult(
            score_value=50,
            score_label=ScoreLabel.WARM,
            rationale="Too short",  # Less than 10 characters
        )

    assert "rationale" in str(exc_info.value)


def test_score_missing_fields():
    """Test missing required fields raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ScoreResult(
            score_value=75,
            score_label=ScoreLabel.HOT,
            # Missing rationale
        )  # type: ignore

    assert "rationale" in str(exc_info.value)


def test_score_labels_mapping():
    """Test all valid score labels."""
    for label in [ScoreLabel.HOT, ScoreLabel.WARM, ScoreLabel.COLD]:
        score = ScoreResult(
            score_value=50,
            score_label=label,
            rationale="Testing all valid score labels.",
        )
        assert score.score_label == label


def test_score_to_dict():
    """Test ScoreResult can be converted to dict."""
    score = ScoreResult(
        score_value=80,
        score_label=ScoreLabel.HOT,
        rationale="Test conversion to dictionary format.",
    )

    score_dict = score.model_dump()

    assert score_dict["score_value"] == 80
    assert score_dict["score_label"] == ScoreLabel.HOT
    assert score_dict["rationale"] == "Test conversion to dictionary format."
