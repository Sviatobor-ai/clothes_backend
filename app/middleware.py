"""Custom FastAPI middleware for logging context propagation."""

from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import RequestResponseEndpoint

from app import logging_conf


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach and propagate a request identifier for each HTTP request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming_request_id = (request.headers.get("X-Request-ID") or "").strip()
        request_id = incoming_request_id or uuid.uuid4().hex
        logging_conf.set_request_id(request_id)

        try:
            response = await call_next(request)
        finally:
            logging_conf.set_request_id(None)
            logging_conf.set_job_context(None, None)

        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id_from_context() -> str | None:
    """Retrieve the current request identifier from the logging context."""

    return logging_conf.get_log_context().get("request_id")
