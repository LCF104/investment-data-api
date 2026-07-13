from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.utils.errors import APIError, ErrorCode


bearer_scheme = HTTPBearer(auto_error=False)


def require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise APIError(
            ErrorCode.UNAUTHORIZED,
            "Missing Authorization bearer token.",
            status.HTTP_401_UNAUTHORIZED,
            user_action="Send Authorization: Bearer <APP_API_TOKEN>.",
        )
    if not settings.app_api_token:
        raise APIError(
            ErrorCode.UNAUTHORIZED,
            "APP_API_TOKEN is not configured on the API server.",
            status.HTTP_401_UNAUTHORIZED,
            user_action="Set APP_API_TOKEN in the deployment environment.",
        )
    if credentials.credentials != settings.app_api_token:
        raise APIError(
            ErrorCode.UNAUTHORIZED,
            "Invalid bearer token.",
            status.HTTP_401_UNAUTHORIZED,
            user_action="Check the token configured in GPT Builder Actions.",
        )

