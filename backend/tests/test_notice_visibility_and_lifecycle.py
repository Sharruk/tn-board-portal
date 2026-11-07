"""
Unit and regression tests for Official Notices visibility, lifecycle,
filtering, and admin vs public API consistency.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.main import app

_NOW = datetime.now(timezone.utc)
_FUTURE_EXPIRY = _NOW + timedelta(days=11)
_PAST_EXPIRY = _NOW - timedelta(days=120)

MOCK_NOTICES = [
    {
        "id": 4,
        "title": "Chennai District Classes 6–9 Second Mid Term Test Timetable November 2026",
        "category": "Mid Term Test",
        "class_id": 9,
        "year": 2026,
        "description": "Portions: October and November.",
        "file_path": "f100b620-020c-4d3f-9a10-d0203d231530.pdf",
        "public_url": "https://example.supabase.co/storage/v1/object/public/official-updates/f100b620.pdf",
        "file_type": "pdf",
        "youtube_url": None,
        "is_visible": False,  # Initially hidden draft
        "is_pinned": False,
        "expires_at": _FUTURE_EXPIRY,
        "view_count": 0,
        "download_count": 0,
        "created_at": _NOW,
        "updated_at": _NOW,
        "class_name": "Class 9",
    },
    {
        "id": 3,
        "title": "TN Board Class 12 Monthly Test Timetable 2026 - Chennai District",
        "category": "Monthly Test Timetable",
        "class_id": 12,
        "year": 2026,
        "description": "Monthly test timetable.",
        "file_path": "4b750e1e-c692-4c8c-b5bb-a7b8db31ed43.pdf",
        "public_url": "https://example.supabase.co/storage/v1/object/public/official-updates/4b750e1e.pdf",
        "file_type": "pdf",
        "youtube_url": "https://youtube.com/shorts/WsBs4BZFJdU",
        "is_visible": True,  # Visible but expired (Archived)
        "is_pinned": False,
        "expires_at": _PAST_EXPIRY,
        "view_count": 39,
        "download_count": 5,
        "created_at": _NOW - timedelta(days=130),
        "updated_at": _NOW,
        "class_name": "Class 12",
    },
    {
        "id": 2,
        "title": "TN Board Class 10 Monthly Test Timetable 2026 - Chennai District",
        "category": "Monthly Test Timetable",
        "class_id": 10,
        "year": 2026,
        "description": "Monthly test timetable.",
        "file_path": "a41ce6b2-f039-4443-afa6-c46311e6e9d3.pdf",
        "public_url": "https://example.supabase.co/storage/v1/object/public/official-updates/a41ce6b2.pdf",
        "file_type": "pdf",
        "youtube_url": None,
        "is_visible": True,  # Visible but expired (Archived)
        "is_pinned": False,
        "expires_at": _PAST_EXPIRY,
        "view_count": 20,
        "download_count": 2,
        "created_at": _NOW - timedelta(days=130),
        "updated_at": _NOW,
        "class_name": "Class 10",
    },
]


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        return self._mapping[key]

    def get(self, key, default=None):
        return self._mapping.get(key, default)


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


def _build_test_db(notices_store: list[dict]):
    mock_db = MagicMock()

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        p = params or {}

        if "select count(*)" in sql:
            # Filter count
            matched = notices_store
            if p.get("is_visible") is not None:
                matched = [n for n in matched if n["is_visible"] == p["is_visible"]]
            if p.get("category") is not None:
                matched = [n for n in matched if n["category"] == p["category"]]
            if p.get("class_id") is not None:
                matched = [n for n in matched if n["class_id"] == p["class_id"]]
            return MockResult(scalar_val=len(matched))

        if "select n.*" in sql:
            matched = list(notices_store)
            if p.get("id") is not None:
                matched = [n for n in matched if n["id"] == p["id"]]
                return MockResult(matched)
            if p.get("is_visible") is not None:
                matched = [n for n in matched if n["is_visible"] == p["is_visible"]]
            if p.get("category") is not None:
                matched = [n for n in matched if n["category"] == p["category"]]
            if p.get("class_id") is not None:
                matched = [n for n in matched if n["class_id"] == p["class_id"]]
            limit = p.get("limit", 50)
            offset = p.get("offset", 0)
            return MockResult(matched[offset : offset + limit])

        if "insert into official_notices" in sql:
            new_id = max(n["id"] for n in notices_store) + 1 if notices_store else 1
            new_notice = {
                "id": new_id,
                "title": p["title"],
                "category": p["category"],
                "class_id": p["class_id"],
                "year": p["year"],
                "description": p["description"],
                "file_path": p["file_path"],
                "public_url": p["public_url"],
                "file_type": p["file_type"],
                "youtube_url": p["youtube_url"],
                "is_visible": p["is_visible"],
                "is_pinned": p["is_pinned"],
                "expires_at": p["expires_at"],
                "view_count": 0,
                "download_count": 0,
                "created_at": _NOW,
                "updated_at": _NOW,
                "class_name": f"Class {p['class_id']}" if p["class_id"] else None,
            }
            notices_store.append(new_notice)
            return MockResult([new_notice])

        if "update official_notices" in sql:
            nid = p["id"]
            for n in notices_store:
                if n["id"] == nid:
                    if "is_visible" in p:
                        n["is_visible"] = p["is_visible"]
                    if "title" in p:
                        n["title"] = p["title"]
                    return MockResult([n])

        if "admin_activity_logs" in sql:
            return MockResult([{"id": "activity-1", "metadata": "{}"}])

        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


@pytest.fixture
def client_fixture():
    store = [dict(n) for n in MOCK_NOTICES]
    mock_db = _build_test_db(store)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }
    client = TestClient(app)
    yield client, store
    app.dependency_overrides.clear()


def test_notice_creation_defaults_to_visible(client_fixture):
    """When is_visible is omitted from upload FormData, it should default to True."""
    client, store = client_fixture
    resp = client.post(
        "/api/v1/notices",
        data={
            "title": "Public Exam Timetable 2026",
            "category": "Public Exam Timetable",
            "year": "2026",
            "class_id": "10",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_visible"] is True
    assert data["category"] == "Public Exam Timetable"
    assert data["class_id"] == 10


def test_notice_creation_respects_explicit_hidden(client_fixture):
    """When an admin explicitly uploads a draft notice with is_visible=false, it remains hidden."""
    client, store = client_fixture
    resp = client.post(
        "/api/v1/notices",
        data={
            "title": "Draft Internal Circular",
            "category": "School Circular",
            "year": "2026",
            "is_visible": "false",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_visible"] is False


def test_public_endpoint_filters_out_hidden_notices(client_fixture):
    """Public listing with is_visible=true excludes draft/hidden notices."""
    client, store = client_fixture
    resp = client.get("/api/v1/notices?is_visible=true")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Should only return the 2 visible notices (ID 3 and 2), not ID 4 which is hidden
    assert len(data) == 2
    assert all(n["is_visible"] is True for n in data)
    assert not any(n["id"] == 4 for n in data)


def test_admin_endpoint_returns_all_notices_including_hidden(client_fixture):
    """Admin listing without is_visible filter returns all notices (both visible and hidden)."""
    client, store = client_fixture
    resp = client.get("/api/v1/notices")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 3
    # ID 4 is present even though is_visible is False
    assert any(n["id"] == 4 and n["is_visible"] is False for n in data)


def test_admin_can_publish_hidden_notice(client_fixture):
    """Admin updates is_visible from False to True, making it appear in public list."""
    client, store = client_fixture
    # Toggle notice 4 to visible
    patch_resp = client.patch("/api/v1/notices/4", json={"is_visible": True})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_visible"] is True

    # Now verify it appears in the public listing
    public_resp = client.get("/api/v1/notices?is_visible=true")
    assert public_resp.status_code == 200
    public_data = public_resp.json()["data"]
    assert any(n["id"] == 4 for n in public_data)


def test_large_limit_supported_up_to_500(client_fixture):
    """Frontend requests with limit=200 should not fail with 422 validation error."""
    client, store = client_fixture
    resp = client.get("/api/v1/notices?limit=200")
    assert resp.status_code == 200


def test_category_and_class_filtering(client_fixture):
    """Filtering by category and class works as expected."""
    client, store = client_fixture
    resp_cat = client.get("/api/v1/notices?category=Mid Term Test")
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()["data"]) == 1
    assert resp_cat.json()["data"][0]["category"] == "Mid Term Test"

    resp_class = client.get("/api/v1/notices?class_id=12")
    assert resp_class.status_code == 200
    assert len(resp_class.json()["data"]) == 1
    assert resp_class.json()["data"][0]["class_id"] == 12


def test_expiry_date_iso_format_consistency(client_fixture):
    """Verify that future and past expiry dates serialize to valid ISO 8601 UTC strings."""
    client, store = client_fixture
    resp = client.get("/api/v1/notices")
    assert resp.status_code == 200
    for notice in resp.json()["data"]:
        if notice.get("expires_at"):
            # Ensure it is a valid ISO format parsable by datetime.fromisoformat
            dt = datetime.fromisoformat(notice["expires_at"].replace("Z", "+00:00"))
            assert dt is not None

