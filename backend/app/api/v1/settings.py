"""Settings and configuration endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_scoring_config_service
from app.models.schemas import ScoringConfigResponse, ScoringConfigUpdate
from app.services.scoring_config_service import ScoringConfigService

router = APIRouter()


@router.get("/scoring-config", response_model=ScoringConfigResponse, tags=["settings"])
async def get_scoring_config(
    user: str = Depends(get_current_user),
    config_service: ScoringConfigService = Depends(get_scoring_config_service),
) -> ScoringConfigResponse:
    """Get the current scoring configuration."""
    config = await config_service.get_config()
    return ScoringConfigResponse.model_validate(config)


@router.put("/scoring-config", response_model=ScoringConfigResponse, tags=["settings"])
async def update_scoring_config(
    config: ScoringConfigUpdate,
    user: str = Depends(get_current_user),
    config_service: ScoringConfigService = Depends(get_scoring_config_service),
) -> ScoringConfigResponse:
    """Update the scoring configuration."""
    result = await config_service.update_config(
        weights=config.weights,
        thresholds=config.thresholds,
        user=user,
    )
    return ScoringConfigResponse.model_validate(result)
