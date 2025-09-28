"""FastAPI application entrypoint for the Nano Banana backend."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from zoneinfo import ZoneInfo

from app.config import settings
from app.logging_conf import configure_logging, set_job_context
from app.middleware import RequestContextMiddleware, get_request_id_from_context
from app.models.dto import HealthResponse, RunNowResponse
from app.queue import enqueue_run_now, queue_size

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nano Banana — Clothes Backend",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(RequestContextMiddleware)


@app.on_event("startup")
async def on_startup() -> None:
    """Emit an informative startup banner."""

    logger.info(
        "%s v%s (env=%s, tz=%s, python=%s, structured_logging=true)",
        app.title,
        app.version,
        settings.app_env,
        settings.tz,
        sys.version.split()[0],
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Log when the application is shutting down."""

    logger.info("application shutdown")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a JSON error when request validation fails."""

    request_id = get_request_id_from_context()
    errors = exc.errors()
    issue_count = len(errors)
    logger.warning(
        "validation error on %s (%d issue(s)) [request_id=%s]",
        request.url.path,
        issue_count,
        request_id,
    )
    response = JSONResponse(
        status_code=422,
        content={"detail": errors, "request_id": request_id},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler that returns a 500 JSON response."""

    request_id = get_request_id_from_context()
    logger.error(
        "unhandled error on %s [%s] %s [request_id=%s]",
        request.url.path,
        exc.__class__.__name__,
        exc,
        request_id,
        exc_info=True,
    )
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return basic service health information."""

    request_id = get_request_id_from_context()
    logger.info("health probe [request_id=%s]", request_id)

    now_utc = datetime.now(timezone.utc)
    local_zone = ZoneInfo(settings.tz)
    now_local = datetime.now(local_zone)
    response = HealthResponse(
        status="ok",
        env=settings.app_env,
        tz=settings.tz,
        now_utc=now_utc.isoformat(),
        now_local=now_local.isoformat(),
        queue_size=queue_size(),
    )
    return response


@app.post("/run-now", response_model=RunNowResponse)
async def run_now() -> RunNowResponse:
    """Queue a new run-now job and return its identifier."""

    job_id = enqueue_run_now()
    try:
        set_job_context(job_id, None)
        logger.info("run-now request accepted [job_id=%s]", job_id)
    finally:
        set_job_context(None, None)
    return RunNowResponse(queued=True, job_id=job_id)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# Run locally: `uvicorn app.main:app --reload`
# Observe logs: `curl -i http://127.0.0.1:8000/health` and `curl -i -X POST http://127.0.0.1:8000/run-now`
