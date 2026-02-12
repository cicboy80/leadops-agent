import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ScoringConfig
from app.repositories.scoring_config_repository import ScoringConfigRepository

logger = structlog.get_logger()

# Exponential moving average alpha for weight adjustments
EMA_ALPHA = 0.1

# Outcome sentiment mapping
POSITIVE_OUTCOMES = {"booked_demo", "closed_won"}
NEGATIVE_OUTCOMES = {"no_response", "closed_lost", "disqualified"}


class ScoringConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_repo = ScoringConfigRepository(session)

    async def get_config(self) -> ScoringConfig:
        """
        Get the active scoring configuration.
        Delegates to repository which returns default if none exists.
        """
        return await self.config_repo.get_active()

    async def update_config(
        self,
        weights: dict | None = None,
        thresholds: dict | None = None,
        user: str = "system",
    ) -> ScoringConfig:
        """
        Update scoring configuration weights and/or thresholds.

        Args:
            weights: Optional dict of weight updates to merge with current
            thresholds: Optional dict of threshold updates to merge with current
            user: User or system identifier making the update

        Returns:
            Updated ScoringConfig
        """
        logger.info("Updating scoring config", user=user, has_weights=weights is not None, has_thresholds=thresholds is not None)

        current_config = await self.get_config()

        # Merge weights if provided
        new_weights = current_config.weights.copy()
        if weights:
            new_weights.update(weights)

        # Merge thresholds if provided
        new_thresholds = current_config.thresholds.copy()
        if thresholds:
            new_thresholds.update(thresholds)

        # Create new config record (versioned history)
        new_config = await self.config_repo.create(
            weights=new_weights,
            thresholds=new_thresholds,
            updated_by=user,
        )

        logger.info("Scoring config updated", config_id=str(new_config.id))

        return new_config

    async def update_weights_from_feedback(
        self,
        outcome: str,
        lead_score: int,
    ) -> ScoringConfig:
        """
        Update scoring weights based on outcome feedback using exponential moving average.

        This is NOT ML or model training - it's a simple heuristic adjustment:
        - If outcome is positive and score was low, increase relevant weights slightly
        - If outcome is negative and score was high, decrease relevant weights slightly

        Uses EMA with alpha=0.1 to smooth adjustments over time.

        Args:
            outcome: Outcome type (e.g., 'booked_demo', 'no_response')
            lead_score: The original score value for the lead

        Returns:
            Updated ScoringConfig
        """
        logger.info("Processing feedback for weight adjustment", outcome=outcome, score=lead_score)

        current_config = await self.get_config()
        weights = current_config.weights.copy()
        thresholds = current_config.thresholds

        # Determine if this is a prediction error
        is_positive = outcome in POSITIVE_OUTCOMES
        is_negative = outcome in NEGATIVE_OUTCOMES

        if not is_positive and not is_negative:
            logger.info("Outcome not relevant for learning, skipping", outcome=outcome)
            return current_config

        hot_threshold = thresholds.get("hot", 70)
        warm_threshold = thresholds.get("warm", 40)

        # Check for prediction mismatch
        score_was_low = lead_score < warm_threshold
        score_was_high = lead_score >= hot_threshold

        adjustment_made = False

        # Case 1: Positive outcome but we scored it low (false negative)
        if is_positive and score_was_low:
            logger.info("Positive outcome with low score - increasing weights")
            # Increase all weights slightly using EMA
            for key in weights:
                old_weight = weights[key]
                # Increase by 5% of current value, smoothed by EMA
                adjustment = old_weight * 0.05
                weights[key] = old_weight + (EMA_ALPHA * adjustment)
            adjustment_made = True

        # Case 2: Negative outcome but we scored it high (false positive)
        elif is_negative and score_was_high:
            logger.info("Negative outcome with high score - decreasing weights")
            # Decrease all weights slightly using EMA
            for key in weights:
                old_weight = weights[key]
                # Decrease by 5% of current value, smoothed by EMA
                adjustment = old_weight * 0.05
                weights[key] = old_weight - (EMA_ALPHA * adjustment)
                # Ensure weights stay positive
                weights[key] = max(weights[key], 0.01)
            adjustment_made = True

        if adjustment_made:
            # Normalize weights to sum to 1.0
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}

            # Create new config with adjusted weights
            new_config = await self.update_config(
                weights=weights,
                user="learning_system",
            )

            logger.info("Weights adjusted from feedback", adjustment_type="increase" if is_positive else "decrease")
            return new_config
        else:
            logger.info("No weight adjustment needed - score aligned with outcome")
            return current_config
