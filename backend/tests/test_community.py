"""
Tests for Community discussions and comments endpoints.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.auth import get_current_user
from app.main import app


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
    posts_res = MagicMock()
    posts_res.data = [
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
    posts_res.count = 1

    comments_res = MagicMock()
    comments_res.data = [
        {"post_id": "post-1"}
    ]

    def table_mock(name):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.in_.return_value = q
        q.order.return_value = q
        q.range.return_value = q
        if name == "community_posts":
            q.execute.return_value = posts_res
        elif name == "community_comments":
            q.execute.return_value = comments_res
        return q

    mock_db.table.side_effect = table_mock

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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
    
    post_res = MagicMock()
    post_res.data = [
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

    comments_res = MagicMock()
    comments_res.data = [
        {
            "id": "comment-1",
            "post_id": "post-1",
            "author_name": "Priya",
            "content": "Very helpful thanks!",
            "created_at": "2024-01-01T01:00:00Z",
        }
    ]

    def table_mock(name):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.order.return_value = q
        if name == "community_posts":
            q.execute.return_value = post_res
        elif name == "community_comments":
            q.execute.return_value = comments_res
        return q

    mock_db.table.side_effect = table_mock

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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
    mock_res = MagicMock()
    mock_res.data = [
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
    mock_query = MagicMock()
    mock_query.insert.return_value = mock_query
    mock_query.execute.return_value = mock_res
    mock_db.table.return_value = mock_query

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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
    
    post_res = MagicMock()
    post_res.data = [{"id": "post-1", "is_deleted": False}]

    comment_res = MagicMock()
    comment_res.data = [
        {
            "id": "new-comment-id",
            "post_id": "post-1",
            "author_name": "Karthik",
            "content": "Here is my reply",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]

    def table_mock(name):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.insert.return_value = q
        if name == "community_posts":
            q.execute.return_value = post_res
        elif name == "community_comments":
            q.execute.return_value = comment_res
        return q

    mock_db.table.side_effect = table_mock

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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
    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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

    post_res = MagicMock()
    post_res.data = [{"id": "post-1", "upvotes": 3, "is_deleted": False}]

    vote_res_empty = MagicMock()
    vote_res_empty.data = []

    def table_mock(name):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.insert.return_value = q
        q.update.return_value = q
        q.delete.return_value = q
        if name == "community_posts":
            q.execute.return_value = post_res
        elif name == "community_post_votes":
            q.execute.return_value = vote_res_empty
        return q

    mock_db.table.side_effect = table_mock

    app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
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
