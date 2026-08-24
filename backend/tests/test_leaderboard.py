"""
Tests for the Leaderboard domain and endpoints.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.db.supabase_client import get_supabase_admin_client
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_submissions_data():
    return [
        {"publisher_name": "Sharruk", "firebase_uid": "uid1", "status": "approved", "created_at": "2024-01-01T00:00:00Z"},
        {"publisher_name": "Sharruk", "firebase_uid": "uid1", "status": "approved", "created_at": "2024-01-02T00:00:00Z"},
        {"publisher_name": "Sharruk", "firebase_uid": "uid1", "status": "pending", "created_at": "2024-01-03T00:00:00Z"},
        {"publisher_name": "Pranav", "firebase_uid": "uid2", "status": "approved", "created_at": "2024-01-01T00:00:00Z"},
        {"publisher_name": "Pranav", "firebase_uid": "uid2", "status": "rejected", "created_at": "2024-01-02T00:00:00Z"},
        {"publisher_name": "Ajith", "firebase_uid": "uid3", "status": "rejected", "created_at": "2024-01-01T00:00:00Z"},
    ]


def test_leaderboard_empty(client):
    """Test leaderboard returns empty list when no submissions exist."""
    mock_db = MagicMock()
    mock_res = MagicMock()
    mock_res.data = []
    
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.execute.return_value = mock_res
    mock_db.table.return_value = mock_query

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
    try:
        response = client.get("/api/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total_contributors"] == 0
    finally:
        app.dependency_overrides.clear()


def test_leaderboard_rankings_and_calculations(client):
    """Test ranking order and acceptance rate calculations."""
    mock_db = MagicMock()
    mock_res = MagicMock()
    mock_res.data = _make_submissions_data()

    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.execute.return_value = mock_res
    mock_db.table.return_value = mock_query

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
    try:
        response = client.get("/api/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_contributors"] == 3
        
        entries = data["data"]
        assert len(entries) == 3

        # Rank 1: Sharruk (2 accepted out of 3 = 66.7%)
        assert entries[0]["rank"] == 1
        assert entries[0]["contributor_name"] == "Sharruk"
        assert entries[0]["total_contributions"] == 3
        assert entries[0]["accepted_contributions"] == 2
        assert entries[0]["acceptance_rate"] == 66.7

        # Rank 2: Pranav (1 accepted out of 2 = 50.0%)
        assert entries[1]["rank"] == 2
        assert entries[1]["contributor_name"] == "Pranav"
        assert entries[1]["total_contributions"] == 2
        assert entries[1]["accepted_contributions"] == 1
        assert entries[1]["acceptance_rate"] == 50.0

        # Rank 3: Ajith (0 accepted out of 1 = 0.0%)
        assert entries[2]["rank"] == 3
        assert entries[2]["contributor_name"] == "Ajith"
        assert entries[2]["total_contributions"] == 1
        assert entries[2]["accepted_contributions"] == 0
        assert entries[2]["acceptance_rate"] == 0.0

        # Verify no private data is leaked
        for entry in entries:
            assert "email" not in entry
            assert "firebase_uid" not in entry
            assert "id" not in entry
    finally:
        app.dependency_overrides.clear()
