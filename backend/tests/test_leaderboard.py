"""
Tests for the Leaderboard domain and endpoints.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.main import app


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data
        self._data = list(data.values())

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        return self._mapping[idx]


class MockResult:
    def __init__(self, rows: list[dict] | None = None, scalar_val=None):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


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
    mock_db.execute.return_value = MockResult([])

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total_contributors"] == 0

        # Verify /api/v1/contributors alias behaves identically
        alias_res = client.get("/api/v1/contributors")
        assert alias_res.status_code == 200
        alias_data = alias_res.json()
        assert alias_data["data"] == []
        assert alias_data["total_contributors"] == 0
    finally:
        app.dependency_overrides.clear()



def test_leaderboard_rankings_and_calculations(client):
    """Test ranking order and acceptance rate calculations."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult(_make_submissions_data())

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_contributors"] == 3
        
        entries = data["data"]
        assert len(entries) == 3

        # Rank 1: Sharruk (2 approved, 0 rejected, 1 pending => 2/2 = 100.0% acceptance rate)
        assert entries[0]["rank"] == 1
        assert entries[0]["contributor_name"] == "Sharruk"
        assert entries[0]["total_contributions"] == 3
        assert entries[0]["accepted_contributions"] == 2
        assert entries[0]["acceptance_rate"] == 100.0

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


def test_leaderboard_canonical_user_name_override(client):
    """Test leaderboard resolves canonical user name for all historical submissions of a user."""
    mock_db = MagicMock()
    # Simulate SQL query returning COALESCE(NULLIF(TRIM(u.display_name), ''), s.publisher_name) as publisher_name
    mock_db.execute.return_value = MockResult([
        {"publisher_name": "Sharruk CSE", "firebase_uid": "uid1", "status": "approved", "created_at": "2024-01-01T00:00:00Z"},
        {"publisher_name": "Sharruk CSE", "firebase_uid": "uid1", "status": "approved", "created_at": "2024-01-02T00:00:00Z"},
    ])

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_contributors"] == 1
        assert data["data"][0]["contributor_name"] == "Sharruk CSE"
        assert data["data"][0]["accepted_contributions"] == 2
    finally:
        app.dependency_overrides.clear()

