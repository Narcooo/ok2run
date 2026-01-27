import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_approval_gate.config import get_settings

bearer = HTTPBearer()


def api_key_to_client_id(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def get_client_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    settings = get_settings()
    if not settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No API keys configured",
        )
    api_key = credentials.credentials
    if api_key not in settings.api_keys:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return api_key_to_client_id(api_key)
