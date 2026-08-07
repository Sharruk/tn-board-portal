"""Pydantic schemas for the health check endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for GET /health."""

    status: str
    version: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"status": "ok", "version": "2.0"}]
        }
    }
