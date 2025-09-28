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
from app.models.dto import HealthResponse, RunNowResponse
from app.queue import enqueue_run_now, queue_size


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nano Banana — Clothes Backend",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


def _configure_logging() -> None:
    """Ensure basic logging configuration is applied once."""

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)


@app.on_event("startup")
async def on_startup() -> None:
    """Perform startup tasks such as logging configuration."""

    _configure_logging()
    logger.info(
        "Starting Nano Banana backend (env=%s, tz=%s, python=%s)",
        settings.app_env,
        settings.tz,
        sys.version.split()[0],
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Log when the application is shutting down."""

    logger.info("Shutting down Nano Banana backend")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a JSON error when request validation fails."""

    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that returns a 500 JSON response."""

    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return basic service health information."""

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
    logger.info("Enqueued run-now job %s", job_id)
    return RunNowResponse(queued=True, job_id=job_id)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# Run locally: `uvicorn app.main:app --reload`
# Endpoints: `curl http://127.0.0.1:8000/health` and `curl -X POST http://127.0.0.1:8000/run-now`
