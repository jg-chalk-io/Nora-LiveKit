"""FastAPI health check server for Nora LiveKit Agent."""

from fastapi import FastAPI
from pydantic import BaseModel

import structlog

log = structlog.get_logger()

app = FastAPI(title="Nora LiveKit Agent", version="0.1.0")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring.

    Returns:
        HealthResponse: Status and service information
    """
    log.debug("health.request")
    return HealthResponse(status="healthy", service="nora-livekit")
