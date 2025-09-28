"""Data transfer objects for the Nano Banana backend API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for the `/health` endpoint."""

    status: str
    env: str
    tz: str
    now_utc: str
    now_local: str
    queue_size: int


class RunNowResponse(BaseModel):
    """Response model for the `/run-now` endpoint."""

    queued: bool
    job_id: str
