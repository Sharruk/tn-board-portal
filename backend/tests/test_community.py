"""
Tests for Community discussions and comments endpoints.
"""

from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
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
    def __init__(self, rows: list[dict | tuple] | None = None, scalar_val=None, rowcount: int = 1):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val
        self.rowcount = rowcount

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


# ── Comment & Post Deletion Authorization Security Tests ──────────────────────

MOCK_OTHER_USER = {
    "firebase_uid": "user-456",
    "email": "other@example.com",
    "display_name": "Other Student",
    "role": "USER",
    "is_active": True,
}

MOCK_ADMIN = {
    "firebase_uid": "admin-123",
    "email": "admin@example.com",
    "display_name": "Admin User",
    "role": "ADMIN",
    "is_active": True,
}

MOCK_SUPER_ADMIN = {
    "firebase_uid": "super-123",
    "email": "super@example.com",
    "display_name": "Super Admin",
    "role": "SUPER_ADMIN",
    "is_active": True,
}

SAMPLE_COMMENT_ROW = {
    "id": "comment-abc-123",
    "post_id": "post-1",
    "firebase_uid": "user-123",  # Owned by MOCK_USER
    "author_name": "Karthik",
    "author_avatar": None,
    "parent_id": None,
    "content": "A student comment that requires authorization to delete",
    "is_deleted": False,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}

SAMPLE_POST_ROW = {
    "id": "post-xyz-789",
    "firebase_uid": "user-123",  # Owned by MOCK_USER
    "author_name": "Karthik",
    "author_avatar": None,
    "title": "Post Title",
    "content": "Post body content",
    "category": "general",
    "status": "open",
    "upvotes": 0,
    "likes_count": 0,
    "comments_count": 0,
    "is_pinned": False,
    "is_deleted": False,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}


def test_admin_can_delete_other_user_comment(client):
    """Admin can moderate (delete) another user's comment."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([SAMPLE_COMMENT_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Comment deleted"}
        # Verify delete statement was executed
        assert any("update community_comments set is_deleted = true" in s[0] or "delete from community_comments" in s[0] for s in executed_statements)
    finally:
        app.dependency_overrides.clear()


def test_super_admin_can_delete_other_user_comment(client):
    """Super Admin can moderate (delete) another user's comment."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([SAMPLE_COMMENT_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_SUPER_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer super-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Comment deleted"}
        assert any("update community_comments set is_deleted = true" in s[0] or "delete from community_comments" in s[0] for s in executed_statements)
    finally:
        app.dependency_overrides.clear()


def test_user_can_delete_own_comment(client):
    """User can delete their own comment."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([SAMPLE_COMMENT_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Comment deleted"}
        assert any("update community_comments set is_deleted = true" in s[0] for s in executed_statements)
    finally:
        app.dependency_overrides.clear()


def test_user_cannot_delete_other_user_comment(client):
    """User attempting to delete another user's comment is rejected with 403 Forbidden."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            # Comment is owned by user-123, but caller is user-456
            return MockResult([SAMPLE_COMMENT_ROW])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_OTHER_USER

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer other-token"},
        )
        assert res.status_code == 403
        assert "You can only delete your own comments" in res.json()["detail"]
        # CRITICAL SECURITY ASSERTION: Delete query was NEVER executed!
        delete_sqls = [s[0] for s in executed_statements if "update community_comments set is_deleted" in s[0] or "delete from community_comments" in s[0]]
        assert len(delete_sqls) == 0, f"Delete statement should not have executed: {delete_sqls}"
    finally:
        app.dependency_overrides.clear()


def test_user_cannot_delete_nonexistent_comment(client):
    """Attempting to delete a nonexistent comment returns 404 Not Found."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([])  # Comment not found
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-missing-999",
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 404
        assert "Comment with id 'comment-missing-999' was not found" in res.json()["detail"]
        # CRITICAL ASSERTION: Delete query was NEVER executed!
        delete_sqls = [s[0] for s in executed_statements if "update community_comments set is_deleted" in s[0] or "delete from community_comments" in s[0]]
        assert len(delete_sqls) == 0
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_user_cannot_delete_comment(client):
    """Unauthenticated delete request returns 401 Unauthorized."""
    res = client.delete("/api/v1/community/comments/comment-abc-123")
    assert res.status_code == 401


def test_disabled_account_cannot_delete_comment(client):
    """Disabled user account returns 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    def _raise_disabled():
        raise HTTPException(status_code=403, detail="Account is disabled.")

    app.dependency_overrides[get_current_user] = _raise_disabled

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer disabled-token"},
        )
        assert res.status_code == 403
        assert "Account is disabled" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_revoked_admin_cannot_delete_other_user_comment(client):
    """Revoked Admin (demoted to USER) cannot delete another user's comment."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([SAMPLE_COMMENT_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    demoted_admin = {
        "firebase_uid": "demoted-admin-uid",
        "email": "demoted@example.com",
        "display_name": "Demoted Admin",
        "role": "USER",
        "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: demoted_admin

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer demoted-token"},
        )
        assert res.status_code == 403
        assert "You can only delete your own comments" in res.json()["detail"]
        delete_sqls = [s[0] for s in executed_statements if "update community_comments set is_deleted" in s[0] or "delete from community_comments" in s[0]]
        assert len(delete_sqls) == 0
    finally:
        app.dependency_overrides.clear()


def test_super_admin_can_delete_other_user_post(client):
    """Super Admin can moderate (delete) another user's post."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_posts" in sql:
            return MockResult([SAMPLE_POST_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_SUPER_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer super-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Post deleted"}
    finally:
        app.dependency_overrides.clear()


def test_user_cannot_delete_other_user_post(client):
    """User attempting to delete another user's post is rejected with 403 Forbidden."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_posts" in sql:
            return MockResult([SAMPLE_POST_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_OTHER_USER

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer other-token"},
        )
        assert res.status_code == 403
        assert "You can only delete your own posts" in res.json()["detail"]
        delete_sqls = [s[0] for s in executed_statements if "update community_posts set is_deleted" in s[0] or "delete from community_posts" in s[0]]
        assert len(delete_sqls) == 0
    finally:
        app.dependency_overrides.clear()


def test_disabled_admin_cannot_delete_comment(client):
    """Disabled admin account (role=ADMIN, is_active=False) is rejected with 403 Forbidden."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([SAMPLE_COMMENT_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db

    disabled_admin = {
        "firebase_uid": "admin-disabled-123",
        "email": "disabled_admin@example.com",
        "display_name": "Disabled Admin",
        "role": "ADMIN",
        "is_active": False,
    }

    def _get_current_user():
        if not disabled_admin.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account is disabled.")
        return disabled_admin

    app.dependency_overrides[get_current_user] = _get_current_user

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer disabled-admin-token"},
        )
        assert res.status_code == 403
        assert "Account is disabled" in res.json()["detail"]
        delete_sqls = [
            s[0] for s in executed_statements
            if "update community_comments set is_deleted" in s[0] or "delete from community_comments" in s[0]
        ]
        assert len(delete_sqls) == 0
    finally:
        app.dependency_overrides.clear()


def test_admin_can_delete_other_user_post(client):
    """Active regular Admin (role=ADMIN) can delete another user's post."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_posts" in sql:
            return MockResult([SAMPLE_POST_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Post deleted"}
        delete_sqls = [
            s[0] for s in executed_statements
            if "update community_posts set is_deleted = true" in s[0] or "delete from community_posts" in s[0]
        ]
        assert len(delete_sqls) == 1
    finally:
        app.dependency_overrides.clear()


def test_user_can_delete_own_post(client):
    """Active regular user can delete their own post."""
    mock_db = MagicMock()
    executed_statements = []

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_posts" in sql:
            return MockResult([SAMPLE_POST_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "message": "Post deleted"}
        delete_sqls = [
            s[0] for s in executed_statements
            if "update community_posts set is_deleted = true" in s[0] or "delete from community_posts" in s[0]
        ]
        assert len(delete_sqls) == 1
    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_already_deleted_comment(client):
    """Attempting to delete an already soft-deleted comment returns 404 Not Found."""
    mock_db = MagicMock()
    executed_statements = []

    DELETED_COMMENT_ROW = {
        **SAMPLE_COMMENT_ROW,
        "is_deleted": True,
    }

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        executed_statements.append((sql, params))
        if "from community_comments" in sql:
            return MockResult([DELETED_COMMENT_ROW])
        return MockResult(rowcount=1)

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 404
        assert "Comment with id 'comment-abc-123' was not found" in res.json()["detail"]
        delete_sqls = [
            s[0] for s in executed_statements
            if "update community_comments set is_deleted" in s[0] or "delete from community_comments" in s[0]
        ]
        assert len(delete_sqls) == 0
    finally:
        app.dependency_overrides.clear()


# ── Stage 3B.4: Moderation Audit Logging Tests ─────────────────────────────

def test_admin_delete_post_records_audit_log(client, monkeypatch):
    """Admin deleting a community post creates a COMMUNITY_POST_DELETED audit log entry."""
    logged_calls = []

    def mock_log_activity(self, **kwargs):
        logged_calls.append(kwargs)
        return {"id": "comm-log-1", **kwargs}

    monkeypatch.setattr(
        "app.repositories.admin_activity_repository.AdminActivityRepository.log_activity",
        mock_log_activity,
    )

    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult([SAMPLE_POST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        assert len(logged_calls) == 1
        call = logged_calls[0]
        assert call["action"] == "COMMUNITY_POST_DELETED"
        assert call["actor_uid"] == MOCK_ADMIN["firebase_uid"]
        assert call["target_type"] == "community_post"
        assert call["target_id"] == "post-xyz-789"
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_admin_delete_comment_records_audit_log(client, monkeypatch):
    """Admin deleting a community comment creates a COMMUNITY_COMMENT_DELETED audit log entry."""
    logged_calls = []

    def mock_log_activity(self, **kwargs):
        logged_calls.append(kwargs)
        return {"id": "comm-log-2", **kwargs}

    monkeypatch.setattr(
        "app.repositories.admin_activity_repository.AdminActivityRepository.log_activity",
        mock_log_activity,
    )

    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult([SAMPLE_COMMENT_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN

    try:
        res = client.delete(
            "/api/v1/community/comments/comment-abc-123",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        assert len(logged_calls) == 1
        call = logged_calls[0]
        assert call["action"] == "COMMUNITY_COMMENT_DELETED"
        assert call["actor_uid"] == MOCK_ADMIN["firebase_uid"]
        assert call["target_type"] == "community_comment"
        assert call["target_id"] == "comment-abc-123"
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_admin_update_report_status_records_audit_log(client, monkeypatch):
    """Admin updating report status creates a CONTENT_REPORT_RESOLVED audit log entry."""
    from app.dependencies.auth import get_current_admin

    logged_calls = []

    def mock_log_activity(self, **kwargs):
        logged_calls.append(kwargs)
        return {"id": "comm-log-3", **kwargs}

    monkeypatch.setattr(
        "app.repositories.admin_activity_repository.AdminActivityRepository.log_activity",
        mock_log_activity,
    )

    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult(rowcount=1)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_admin] = lambda: MOCK_ADMIN

    try:
        res = client.patch(
            "/api/v1/community/reports/report-123?status=actioned",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        assert len(logged_calls) == 1
        call = logged_calls[0]
        assert call["action"] == "CONTENT_REPORT_RESOLVED"
        assert call["target_type"] == "content_report"
        assert call["target_id"] == "report-123"
        assert call["metadata"]["status"] == "actioned"
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_user_delete_own_post_does_not_audit_log(client, monkeypatch):
    """Regular user deleting their own post does NOT log to admin activity."""
    logged_calls = []

    def mock_log_activity(self, **kwargs):
        logged_calls.append(kwargs)
        return {"id": "comm-log-4", **kwargs}

    monkeypatch.setattr(
        "app.repositories.admin_activity_repository.AdminActivityRepository.log_activity",
        mock_log_activity,
    )

    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult([SAMPLE_POST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    try:
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 200
        assert len(logged_calls) == 0
    finally:
        app.dependency_overrides.clear()


def test_admin_delete_post_audit_failure_rolls_back(monkeypatch):
    """If audit log insertion fails during admin deletion, transaction is rolled back."""
    def mock_log_activity(self, **kwargs):
        raise RuntimeError("Audit table unavailable")

    monkeypatch.setattr(
        "app.repositories.admin_activity_repository.AdminActivityRepository.log_activity",
        mock_log_activity,
    )

    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult([SAMPLE_POST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN

    try:
        client = TestClient(app, raise_server_exceptions=False)
        res = client.delete(
            "/api/v1/community/posts/post-xyz-789",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 500
        assert mock_db.rollback.called
    finally:
        app.dependency_overrides.clear()
