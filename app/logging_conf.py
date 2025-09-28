"""Application-level structured logging configuration utilities."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings

_ctx_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_ctx_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "job_id", default=None
)
_ctx_run_number: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "run_number", default=None
)


_ZONE = ZoneInfo(settings.tz)


class _JsonLogFormatter(logging.Formatter):
    """Serialize log records into single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_context = get_log_context()
        timestamp = datetime.now(_ZONE).isoformat(
            timespec="milliseconds"
        )

        message: str
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            message = str(record.msg)

        payload: dict[str, Any] = {
            "ts": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": message,
            "request_id": log_context.get("request_id"),
            "job_id": log_context.get("job_id"),
            "run_number": log_context.get("run_number"),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger to emit JSON logs with shared context."""

    global _configured
    if _configured:
        logging.getLogger().setLevel(level)
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_JsonLogFormatter())
    root_logger.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.setLevel(level)
        uvicorn_logger.propagate = True

    _configured = True


def set_request_id(value: str | None) -> None:
    """Set the current request identifier in the logging context."""

    _ctx_request_id.set(value)


def set_job_context(job_id: str | None, run_number: int | None) -> None:
    """Set the job correlation identifiers in the logging context."""

    _ctx_job_id.set(job_id)
    _ctx_run_number.set(run_number)


def get_log_context() -> dict[str, Any]:
    """Return a shallow copy of the current logging context values."""

    return {
        "request_id": _ctx_request_id.get(),
        "job_id": _ctx_job_id.get(),
        "run_number": _ctx_run_number.get(),
    }
