from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(api_key: str | None = Security(api_key_header)) -> str:
    """Validate API key and return user identifier.

    For MVP, validates against a single configured key.
    Path to Azure Entra ID: replace this with token validation.
    """
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return "default-user"


# Dependency alias for route use
require_auth = Depends(get_current_user)
