"""
Tests for Analytics telemetry and Admin Dashboard aggregation.
"""

from unittest.mock import MagicMock
import pytest
from starlette.testclient import TestClient

from app.dependencies.auth import get_current_admin, get_current_user_optional
from app.dependencies.supabase import get_db
from app.main import app


class MockResult:
    def __init__(self, rows=None, scalar_val=None):
        self._rows = rows or []
        self._scalar = scalar_val

    def fetchall(self):
        return [MagicMock(_mapping=r) if isinstance(r, dict) else r for r in self._rows]

    def fetchone(self):
        if self._rows:
            r = self._rows[0]
            return MagicMock(_mapping=r) if isinstance(r, dict) else r
        return None

    def scalar(self):
        return self._scalar


@pytest.fixture
def client():
    return TestClient(app)


def test_log_analytics_event_anonymous(client):
    """Test recording anonymous client usage event."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        payload = {
            "event_type": "page_view",
            "session_id": "anon-sess-123",
            "metadata": {"path": "/contributors"},
        }
        res = client.post("/api/v1/analytics/event", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
    finally:
        app.dependency_overrides.clear()


def test_log_analytics_paper_view_and_download(client):
    """Test recording paper views and downloads."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([])

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        # Paper view
        res = client.post(
            "/api/v1/analytics/event",
            json={"event_type": "paper_view", "paper_id": 14, "class_id": 10, "subject_id": 5},
        )
        assert res.status_code == 200

        # Download event
        res = client.post(
            "/api/v1/analytics/event",
            json={"event_type": "download", "paper_id": 14},
        )
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_get_analytics_dashboard_admin(client):
    """Test admin retrieving aggregated analytics dashboard."""
    mock_db = MagicMock()

    stats_row = {
        "visitors": 150,
        "page_views": 850,
        "paper_views": 320,
        "downloads": 110,
        "searches": 45,
        "likes": 28,
        "comments": 14,
    }

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from analytics_events" in sql and "to_char" in sql:
            # Daily trends
            return MockResult([{"date": "2026-08-30", "visitors": 150, "page_views": 850, "paper_views": 320, "downloads": 110}])
        elif "where ae.event_type = 'paper_view'" in sql:
            return MockResult([{"id": 14, "name": "Class 10 Maths", "count": 85}])
        elif "where ae.event_type = 'download'" in sql:
            return MockResult([{"id": 14, "name": "Class 10 Maths", "count": 42}])
        elif "classes" in sql:
            return MockResult([{"id": 10, "name": "Class 10", "count": 120}])
        elif "subjects" in sql:
            return MockResult([{"id": 5, "name": "Mathematics", "count": 95}])
        elif "metadata->>'q'" in sql:
            return MockResult([{"name": "maths quarterly", "count": 30}])
        return MockResult([stats_row])

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_admin] = lambda: {"role": "ADMIN", "firebase_uid": "admin-1"}
    try:
        res = client.get("/api/v1/analytics/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["today"]["visitors"] == 150
        assert data["today"]["paper_views"] == 320
        assert data["today"]["downloads"] == 110
        assert len(data["top_viewed_papers"]) == 1
        assert data["top_viewed_papers"][0]["name"] == "Class 10 Maths"
    finally:
        app.dependency_overrides.clear()
