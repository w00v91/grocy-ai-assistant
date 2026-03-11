from datetime import datetime, timezone
from http import HTTPStatus
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    status: int
    path: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    details: list[dict] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiError


def _default_error_code(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).name.lower()
    except ValueError:
        return "internal_server_error"


def build_error_response(
    request: Request,
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: list[dict] | None = None,
) -> JSONResponse:
    payload = build_error_payload(
        request,
        status_code=status_code,
        message=message,
        code=code,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def build_error_payload(
    request: Request,
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: list[dict] | None = None,
) -> ApiErrorResponse:
    return ApiErrorResponse(
        error=ApiError(
            code=code or _default_error_code(status_code),
            message=message,
            status=status_code,
            path=request.url.path,
            details=details or [],
        )
    )


def log_api_error(
    logger: logging.Logger,
    *,
    request: Request,
    status_code: int,
    message: str,
    code: str | None = None,
    details: list[dict] | None = None,
    exc: Exception | None = None,
) -> None:
    payload = build_error_payload(
        request,
        status_code=status_code,
        message=message,
        code=code,
        details=details,
    )
    error = payload.error

    logger.log(
        logging.ERROR if status_code >= 500 else logging.WARNING,
        "api_error code=%s status=%s path=%s message=%s details=%s",
        error.code,
        error.status,
        error.path,
        error.message,
        error.details,
        exc_info=exc,
    )
