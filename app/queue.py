"""Lightweight in-memory queue stubs for the Nano Banana backend."""

from __future__ import annotations

import asyncio
import logging
import uuid

from app import logging_conf


logger = logging.getLogger(__name__)

_queue: asyncio.Queue[str] = asyncio.Queue()


def enqueue_run_now() -> str:
    """Enqueue a placeholder run-now job and return its identifier."""

    job_id = str(uuid.uuid4())
    try:
        logging_conf.set_job_context(job_id, None)
        _queue.put_nowait(job_id)
        logger.info("job enqueued (stub)")
    except asyncio.QueueFull:
        logger.warning("Queue is full; job %s could not be enqueued", job_id)
    finally:
        logging_conf.set_job_context(None, None)
    return job_id


def queue_size() -> int:
    """Return the number of queued jobs."""

    return _queue.qsize()
