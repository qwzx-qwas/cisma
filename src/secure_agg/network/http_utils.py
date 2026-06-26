"""Small JSON HTTP helpers shared by demo servers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from http.server import BaseHTTPRequestHandler
from typing import Any

from secure_agg.exceptions import (
    CommunicationError,
    DimensionMismatchError,
    DuplicateMessageError,
    InvalidRoundStateError,
    InvalidShareError,
    RoundTimeoutError,
    UnknownParticipantError,
)


@dataclass(frozen=True)
class HttpError(Exception):
    """Error with an HTTP status code and public message."""

    status_code: int
    message: str


def exception_to_http_error(exc: Exception) -> HttpError:
    """Map project exceptions to HTTP errors."""
    if isinstance(exc, HttpError):
        return exc
    if isinstance(exc, ValueError):
        return HttpError(400, str(exc))
    if isinstance(exc, UnknownParticipantError):
        return HttpError(403, str(exc))
    if isinstance(exc, DuplicateMessageError):
        return HttpError(409, str(exc))
    if isinstance(exc, InvalidRoundStateError):
        return HttpError(409, str(exc))
    if isinstance(exc, DimensionMismatchError):
        return HttpError(422, str(exc))
    if isinstance(exc, InvalidShareError):
        return HttpError(422, str(exc))
    if isinstance(exc, RoundTimeoutError):
        return HttpError(504, str(exc))
    if isinstance(exc, CommunicationError):
        return HttpError(502, str(exc))
    return HttpError(500, "internal server error")


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    """Read a JSON object from an HTTP request body."""
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length) if content_length else b"{}"
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HttpError(400, "request body must be valid JSON") from exc
    if not isinstance(data, dict):
        raise HttpError(400, "request body must be a JSON object")
    return data


def send_json(
    handler: BaseHTTPRequestHandler,
    status_code: int,
    payload: dict[str, Any],
) -> None:
    """Write a JSON response."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_error_json(handler: BaseHTTPRequestHandler, exc: Exception) -> None:
    """Write a structured JSON error response."""
    http_error = exception_to_http_error(exc)
    send_json(
        handler,
        http_error.status_code,
        {
            "status": "error",
            "error": http_error.message,
        },
    )
