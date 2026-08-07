"""
Basic health check tests.

Run with:
    cd backend
    pip install httpx pytest
    pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /api/v1/health must return HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_body():
    """GET /api/v1/health must return the correct JSON body."""
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0"


def test_root_returns_200():
    """GET / must return HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_response_body():
    """GET / must return project metadata fields."""
    response = client.get("/")
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "environment" in data
    assert data["health"] == "/health"
    assert data["api_v1"] == "/api/v1"


def test_docs_available():
    """Swagger docs must be accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
