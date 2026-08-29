"""
Tests for Paper Likes, Duplicate Like Prevention, and Paper Comments.
"""

from unittest.mock import MagicMock
import pytest
from starlette.testclient import TestClient

from app.dependencies.auth import get_current_user, get_current_user_optional
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


_MOCK_PAPER = {
    "id": 14,
    "subject_id": 5,
    "exam_type": "Monthly Test",
    "year": 2026,
    "month": "July",
    "district": "Chennai",
    "title": "Class 10 Social Science Monthly Test July 2026",
    "paper_type": "question",
    "file_path": "test.pdf",
    "public_url": "https://example.com/test.pdf",
    "original_filename": "Class10_Social_Science.pdf",
    "is_visible": True,
    "download_count": 5,
    "created_at": "2026-08-30T00:00:00Z",
    "subject_name": "Social Science",
    "subject_slug": "social-science",
    "is_practical": False,
    "class_id": 10,
    "class_name": "Class 10",
    "class_slug": "10",
}


def test_toggle_paper_like(client):
    """Test liking and unliking a paper with duplicate prevention."""
    mock_db = MagicMock()

    # Track like state in test mock
    likes_state = set()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from papers" in sql:
            return MockResult([_MOCK_PAPER])
        elif "select id from paper_likes" in sql:
            if ("uid-123", 14) in likes_state:
                return MockResult([{"id": "like-1"}])
            return MockResult([])
        elif "insert into paper_likes" in sql:
            likes_state.add(("uid-123", 14))
            return MockResult([])
        elif "delete from paper_likes" in sql:
            likes_state.discard(("uid-123", 14))
            return MockResult([])
        elif "select count(*)" in sql and "paper_likes" in sql:
            return MockResult([], scalar_val=len(likes_state))
        return MockResult([])

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "firebase_uid": "uid-123", "display_name": "Student A"}

    try:
        # First like: toggles ON
        res1 = client.post("/api/v1/papers/14/like")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["has_liked"] is True
        assert data1["likes_count"] == 1

        # Second like: toggles OFF (unlike)
        res2 = client.post("/api/v1/papers/14/like")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["has_liked"] is False
        assert data2["likes_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_paper_comments_flow(client):
    """Test adding and reading paper comments."""
    mock_db = MagicMock()

    mock_comments = [
        {
            "id": "c1",
            "paper_id": 14,
            "firebase_uid": "uid-1",
            "author_name": "Student A",
            "author_avatar": None,
            "parent_id": None,
            "content": "Very helpful paper, thank you!",
            "is_deleted": False,
            "created_at": "2026-08-30T00:00:00Z",
            "updated_at": "2026-08-30T00:00:00Z",
        },
        {
            "id": "c2",
            "paper_id": 14,
            "firebase_uid": "uid-2",
            "author_name": "Student B",
            "author_avatar": None,
            "parent_id": "c1",
            "content": "Agreed! Do you have the answer key as well?",
            "is_deleted": False,
            "created_at": "2026-08-30T00:05:00Z",
            "updated_at": "2026-08-30T00:05:00Z",
        },
    ]

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from papers" in sql:
            return MockResult([_MOCK_PAPER])
        elif "from paper_comments" in sql:
            return MockResult(mock_comments)
        elif "insert into paper_comments" in sql:
            return MockResult([mock_comments[0]])
        return MockResult([])

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "firebase_uid": "uid-1", "display_name": "Student A"}

    try:
        # Read comments
        res = client.get("/api/v1/papers/14/comments")
        assert res.status_code == 200
        comments = res.json()
        assert len(comments) == 1
        assert comments[0]["content"] == "Very helpful paper, thank you!"
        assert len(comments[0]["replies"]) == 1
        assert comments[0]["replies"][0]["content"] == "Agreed! Do you have the answer key as well?"

        # Post comment
        post_res = client.post(
            "/api/v1/papers/14/comments",
            json={"content": "New comment text"},
        )
        assert post_res.status_code == 201
    finally:
        app.dependency_overrides.clear()
