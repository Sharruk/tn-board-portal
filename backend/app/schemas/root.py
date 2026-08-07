"""Pydantic schemas for the root endpoint."""

from typing import Dict

from pydantic import BaseModel


class RootResponse(BaseModel):
    """Response model for GET /."""

    name: str
    version: str
    environment: str
    docs: str
    health: str
    api_v1: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "TN Board Portal API",
                    "version": "2.0.0",
                    "environment": "development",
                    "docs": "/docs",
                    "health": "/health",
                    "api_v1": "/api/v1",
                }
            ]
        }
    }
