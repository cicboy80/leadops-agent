"""Learning update node — adjusts scoring weights based on outcome feedback."""

import json
import time
from pathlib import Path

from app.models.graph_state import LeadProcessingState


async def learning_update(state: LeadProcessingState) -> dict:
    """Update scoring weights based on outcome feedback.

    This is NOT ML or model training — just simple exponential moving average
    weight adjustment based on which features correlate with good outcomes.

    Reads scoring config from /data/scoring_config.json, adjusts weights, writes back.
    """
    start = time.time()

    errors = []

    try:
        # Path to scoring config
        config_path = Path("/Users/clydecossey/Documents/Claude/leadops_agent/data/scoring_config.json")

        # Default config if file doesn't exist
        default_config = {
            "weights": {
                "urgency_high": 30,
                "urgency_medium": 20,
                "urgency_low": 10,
                "has_budget": 15,
                "has_pain_point": 15,
                "company_size_enterprise": 20,
                "company_size_mid_market": 15,
                "company_size_small": 10,
                "source_referral": 10,
                "source_event": 8,
                "source_partner": 7,
                "source_web_form": 5,
                "source_outbound": 3,
            },
            "learning_rate": 0.1,
            "update_count": 0,
        }

        # Load existing config or use default
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = default_config
            # Ensure data directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

        # Simple weight adjustment logic based on feedback
        # In a real system, this would be triggered by outcome feedback (e.g., booked_demo)
        # For now, this is a placeholder that demonstrates the structure
        learning_rate = config.get("learning_rate", 0.1)
        weights = config["weights"]

        # Get outcome feedback from state if available
        outcome = state.get("outcome_feedback")

        if outcome:
            outcome_type = outcome.get("outcome_type")  # e.g., "booked_demo", "no_response"
            lead_features = outcome.get("lead_features", {})  # Features that were present

            # Positive outcomes: increase weights of present features
            # Negative outcomes: decrease weights of present features
            adjustment = 1.0 if outcome_type in ["booked_demo", "closed_won"] else -1.0

            for feature, value in lead_features.items():
                if value and feature in weights:
                    # Exponential moving average update
                    weights[feature] = weights[feature] * (1 - learning_rate) + (
                        weights[feature] * (1 + learning_rate * adjustment)
                    ) * learning_rate

                    # Clamp weights to reasonable bounds
                    weights[feature] = max(0, min(50, weights[feature]))

            config["update_count"] = config.get("update_count", 0) + 1

        # Write updated config back
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    except Exception as e:
        errors.append(f"Learning update failed: {str(e)}")

    elapsed = time.time() - start

    return {
        "errors": errors,
        "node_timings": {**state.get("node_timings", {}), "learning_update": elapsed},
    }
