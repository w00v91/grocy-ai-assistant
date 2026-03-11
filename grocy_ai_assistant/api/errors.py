from datetime import datetime, timezone
from http import HTTPStatus

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
    payload = ApiErrorResponse(
        error=ApiError(
            code=code or _default_error_code(status_code),
            message=message,
            status=status_code,
            path=request.url.path,
            details=details or [],
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())
