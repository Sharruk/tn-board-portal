"""
Tests for Community discussions and comments endpoints.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.dependencies.supabase import get_db
from app.main import app


class MockRow:
    def __init__(self, data: dict | tuple):
        if isinstance(data, dict):
            self._mapping = data
            self._data = list(data.values())
        else:
            self._mapping = {f"col_{i}": v for i, v in enumerate(data)}
            self._data = list(data)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        return self._mapping[idx]


class MockResult:
    def __init__(self, rows: list[dict | tuple] | None = None, scalar_val=None):
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


MOCK_USER = {
    "firebase_uid": "user-123",
    "email": "student@example.com",
    "display_name": "Karthik",
    "role": "USER",
    "is_active": True,
}


def test_list_posts_public(client):
    """Test public listing of community posts."""
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from community_comments" in sql:
            return MockResult([("post-1", 1)])
        if "count(*)" in sql:
            return MockResult([], scalar_val=1)

        return MockResult(
            [
                {
                    "id": "post-1",
                    "author_name": "Karthik",
                    "title": "Maths Exam Preparation",
                    "content": "Tips for Class 12 Calculus",
                    "upvotes": 5,
                    "is_pinned": False,
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ]
        )


    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get("/api/v1/community/posts")
        assert res.status_code == 200
        data = res.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Maths Exam Preparation"
        assert data["data"][0]["reply_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_get_post_by_id_public(client):
    """Test retrieving a single post with its comments."""
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from community_comments" in sql:
            return MockResult(
                [
                    {
                        "id": "comment-1",
                        "post_id": "post-1",
                        "author_name": "Priya",
                        "content": "Very helpful thanks!",
                        "created_at": "2024-01-01T01:00:00Z",
                    }
                ]
            )
        return MockResult(
            [
                {
                    "id": "post-1",
                    "author_name": "Karthik",
                    "title": "Maths Exam Preparation",
                    "content": "Tips for Class 12 Calculus",
                    "upvotes": 5,
                    "is_pinned": False,
                    "created_at": "2024-01-01T00:00:00Z",
                    "is_deleted": False,
                }
            ]
        )

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get("/api/v1/community/posts/post-1")
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Maths Exam Preparation"
        assert len(data["comments"]) == 1
        assert data["comments"][0]["author_name"] == "Priya"
    finally:
        app.dependency_overrides.clear()


def test_create_post_unauthorized(client):
    """Test creating a post without auth fails with 401."""
    res = client.post("/api/v1/community/posts", json={"title": "Test Title", "content": "Test content"})
    assert res.status_code == 401


def test_create_post_authenticated(client):
    """Test creating a post with valid auth succeeds."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult(
        [
            {
                "id": "new-post-id",
                "author_name": "Karthik",
                "title": "New Discussion Topic",
                "content": "Detailed body text for discussion",
                "upvotes": 0,
                "is_pinned": False,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    try:
        res = client.post(
            "/api/v1/community/posts",
            json={"title": "New Discussion Topic", "content": "Detailed body text for discussion"},
            headers={"Authorization": "Bearer dummy-token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "new-post-id"
        assert data["author_name"] == "Karthik"
    finally:
        app.dependency_overrides.clear()


def test_add_comment_authenticated(client):
    """Test replying to a post."""
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into community_comments" in sql:
            return MockResult(
                [
                    {
                        "id": "new-comment-id",
                        "post_id": "post-1",
                        "author_name": "Karthik",
                        "content": "Here is my reply",
                        "created_at": "2024-01-01T00:00:00Z",
                    }
                ]
            )
        return MockResult([{"id": "post-1", "is_deleted": False}])

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    try:
        res = client.post(
            "/api/v1/community/posts/post-1/comments",
            json={"content": "Here is my reply"},
            headers={"Authorization": "Bearer dummy-token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "Here is my reply"
        assert data["author_name"] == "Karthik"
    finally:
        app.dependency_overrides.clear()


def test_create_post_validation(client):
    """Test validation errors for empty / too short post."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    try:
        res = client.post(
            "/api/v1/community/posts",
            json={"title": "a", "content": "b"},
            headers={"Authorization": "Bearer dummy-token"},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_toggle_upvote_authenticated(client):
    """Test toggling upvote on a post."""
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from community_post_votes" in sql:
            return MockResult([])  # no existing vote
        if "from community_posts" in sql:
            return MockResult([{"id": "post-1", "upvotes": 3, "is_deleted": False}])
        return MockResult([])

    mock_db.execute.side_effect = _execute

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    try:
        res = client.post(
            "/api/v1/community/posts/post-1/upvote",
            headers={"Authorization": "Bearer dummy-token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["upvotes"] == 4
        assert data["voted"] is True
    finally:
        app.dependency_overrides.clear()
