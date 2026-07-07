from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class ErrorCode:
    UNAUTHORIZED = "UNAUTHORIZED"
    MISSING_PROVIDER_KEY = "MISSING_PROVIDER_KEY"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    DATA_SOURCE_UNAVAILABLE = "DATA_SOURCE_UNAVAILABLE"
    DATA_STALE = "DATA_STALE"
    DATA_NOT_IMPLEMENTED = "DATA_NOT_IMPLEMENTED"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PROVIDER_RESPONSE_INVALID = "PROVIDER_RESPONSE_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class APIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        user_action: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.user_action = user_action or ""
        super().__init__(message)


def error_payload(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    user_action: str | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "user_action": user_action or "",
        }
    }


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details, exc.user_action),
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            ErrorCode.INTERNAL_ERROR,
            "Unexpected server error.",
            {"type": exc.__class__.__name__},
            "Please check server logs and try again.",
        ),
    )
