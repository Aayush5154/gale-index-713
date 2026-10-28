"""Typed application errors and sanitised API error payloads."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for errors that are safe to expose to API clients."""

    status_code = 500
    code = "internal_error"
    default_message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def to_payload(self, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }
        if request_id:
            payload["error"]["request_id"] = request_id
        return payload


class InvalidQueryError(AppError):
    status_code = 422
    code = "invalid_query"
    default_message = "The request parameters are invalid."


class UpstreamError(AppError):
    status_code = 503
    code = "upstream_unavailable"
    default_message = "The Elexon data source is currently unavailable."


class UpstreamResponseError(AppError):
    status_code = 502
    code = "upstream_invalid_response"
    default_message = "The Elexon data source returned an invalid response."


class DataUnavailableError(AppError):
    status_code = 503
    code = "data_unavailable"
    default_message = "No data is available for the requested period."
