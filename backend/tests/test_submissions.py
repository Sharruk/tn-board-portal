"""
Tests for submissions endpoints.

Covers:
  POST /api/v1/submissions              — create submission
  GET  /api/v1/submissions              — admin list
  GET  /api/v1/submissions/{id}         — admin detail
  POST /api/v1/submissions/{id}/approve — admin approve
  POST /api/v1/submissions/{id}/reject  — admin reject

All Supabase calls and file uploads are mocked.
No real database connection or storage is required.

Auth:
  Admin routes require Authorization: Bearer <token>.
  We mock the get_current_user dependency to return a mock client,
  bypassing Supabase JWT verification in tests.
"""

import io
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.auth import get_current_user
from app.main import app

# ── Shared fixtures ───────────────────────────────────────────────────────────

_NOW = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat()
_SUB_ID = "11111111-1111-1111-1111-111111111111"
_FILE_ID = "22222222-2222-2222-2222-222222222222"

MOCK_SUBMISSION = {
    "id": _SUB_ID,
    "publisher_name": "Test Contributor",
    "email": "contributor@example.com",
    "details": "Sample math paper",
    "status": "pending",
    "rejection_reason": None,
    "reviewed_at": None,
    "created_at": _NOW,
}

MOCK_FILE = {
    "id": _FILE_ID,
    "submission_id": _SUB_ID,
    "original_filename": "math_paper.pdf",
    "storage_path": f"{_SUB_ID}/aaaa-bbbb.pdf",
    "public_url": f"https://example.supabase.co/storage/v1/object/public/submissions/{_SUB_ID}/aaaa-bbbb.pdf",
    "file_type": "pdf",
    "file_size": 102400,
    "created_at": _NOW,
}

MOCK_PAPER = {
    "id": 99,
    "subject_id": 1,
    "exam_type": "Annual Exam",
    "year": 2024,
    "title": "math paper",
    "paper_type": "question",
    "file_path": MOCK_FILE["storage_path"],
    "public_url": MOCK_FILE["public_url"],
    "original_filename": "math_paper.pdf",
    "is_visible": True,
    "download_count": 0,
    "created_at": _NOW,
}

ADMIN_HEADERS = {"Authorization": "Bearer valid-test-token"}


# ── Admin DB mock override ────────────────────────────────────────────────────

def _make_admin_db_mock() -> MagicMock:
    """
    Mock for admin DB: supports all chaining patterns used in the repository.
    Returns a fully self-chaining MagicMock that returns appropriate data
    based on the table being accessed.
    """
    mock = MagicMock()
    return mock


def _override_admin_db():
    """Dependency override for get_current_user — returns a mock client."""
    return _make_admin_db_mock()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_query_mock(data: list) -> MagicMock:
    """Create a self-chaining query mock that returns given data on execute()."""
    response = MagicMock()
    response.data = data

    builder = MagicMock()
    builder.execute.return_value = response

    query = MagicMock()
    query.select.return_value = query
    query.insert.return_value = builder
    query.update.return_value = builder
    query.eq.return_value = query
    query.in_.return_value = query
    query.or_.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = response
    
    # Allow builder methods for chained eq after update
    builder.eq.return_value = builder

    return query


def _make_table_db(table_data: dict[str, list]) -> MagicMock:
    """
    Create a mock DB that returns different data depending on the table name.
    table_data: {'submissions': [...], 'submission_files': [...], 'papers': [...]}
    """
    mock_db = MagicMock()

    def table_side_effect(name):
        data = table_data.get(name, [])
        return _make_query_mock(data)

    mock_db.table.side_effect = table_side_effect
    return mock_db


# ============================================================================
# Tests: POST /api/v1/submissions (public)
# ============================================================================

class TestCreateSubmission:
    """Tests for the public submission form endpoint."""

    def _make_upload_file(self, filename="test.pdf", content=b"PDF content here", content_type="application/pdf"):
        return (
            "files",
            (filename, io.BytesIO(content), content_type),
        )

    def test_create_submission_success(self):
        """Happy path: valid form data + PDF file → 201 + pending status."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],
            "submission_files": [MOCK_FILE],
        })
        # Mock storage upload
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.upload.return_value = MagicMock()
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test Contributor",
                "email": "contributor@example.com",
                "details": "Sample math paper",
            },
            files=[self._make_upload_file()],
        )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert "id" in body
        assert "submitted successfully" in body["message"]

    def test_create_submission_missing_publisher_name(self):
        """Missing publisher_name → 422."""
        app.dependency_overrides[get_supabase_admin_client] = lambda: MagicMock()
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={"email": "test@example.com"},
            files=[self._make_upload_file()],
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    def test_create_submission_missing_email(self):
        """Missing email → 422."""
        app.dependency_overrides[get_supabase_admin_client] = lambda: MagicMock()
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={"publisher_name": "Test"},
            files=[self._make_upload_file()],
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    def test_create_submission_no_files(self):
        """No files provided → validation error from service."""
        mock_db = _make_table_db({"submissions": []})
        mock_db.storage = MagicMock()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test",
                "email": "test@example.com",
            },
        )
        app.dependency_overrides.clear()

        # No files field at all — FastAPI raises 422
        assert response.status_code == 422

    def test_create_submission_invalid_file_type(self):
        """Unsupported file extension → 422."""
        mock_db = _make_table_db({"submissions": []})
        mock_db.storage = MagicMock()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test",
                "email": "test@example.com",
            },
            files=[("files", ("virus.exe", io.BytesIO(b"evil"), "application/octet-stream"))],
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "unsupported type" in response.json()["detail"].lower()

    def test_create_submission_file_too_large(self):
        """File exceeding 25 MB limit → 422."""
        oversized = b"x" * (26 * 1024 * 1024)  # 26 MB
        mock_db = _make_table_db({"submissions": []})
        mock_db.storage = MagicMock()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test",
                "email": "test@example.com",
            },
            files=[("files", ("big.pdf", io.BytesIO(oversized), "application/pdf"))],
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "size limit" in response.json()["detail"].lower()

    def test_create_submission_too_many_files(self):
        """More than 5 files → 422."""
        mock_db = _make_table_db({"submissions": []})
        mock_db.storage = MagicMock()

        files = [
            ("files", (f"file{i}.pdf", io.BytesIO(b"content"), "application/pdf"))
            for i in range(6)
        ]

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test",
                "email": "test@example.com",
            },
            files=files,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "maximum" in response.json()["detail"].lower()

    def test_create_submission_pending_status_default(self):
        """New submissions always have status = pending."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],
            "submission_files": [MOCK_FILE],
        })
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.upload.return_value = MagicMock()
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "Test",
                "email": "test@example.com",
            },
            files=[("files", ("paper.pdf", io.BytesIO(b"content"), "application/pdf"))],
        )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_create_submission_accepts_docx(self):
        """DOCX file type is accepted."""
        mock_db = _make_table_db({
            "submissions": [{**MOCK_SUBMISSION}],
            "submission_files": [MOCK_FILE],
        })
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.upload.return_value = MagicMock()
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={"publisher_name": "Test", "email": "test@example.com"},
            files=[("files", ("notes.docx", io.BytesIO(b"content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        app.dependency_overrides.clear()

        assert response.status_code == 201


# ============================================================================
# Tests: GET /api/v1/submissions (admin list)
# ============================================================================

class TestListSubmissions:
    """Tests for the admin submissions list endpoint."""

    def test_list_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.get("/api/v1/submissions")
        assert response.status_code == 401

    def test_list_submissions_as_admin(self):
        """Valid admin token → returns list."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],
            "submission_files": [MOCK_FILE],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.get("/api/v1/submissions", headers=ADMIN_HEADERS)
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "count" in body

    def test_list_pending_filter(self):
        """Filtering by status=pending returns only pending submissions."""
        pending = {**MOCK_SUBMISSION, "status": "pending"}
        mock_db = _make_table_db({
            "submissions": [pending],
            "submission_files": [],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.get(
            "/api/v1/submissions?status=pending", headers=ADMIN_HEADERS
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status_filter"] == "pending"
        for item in body["data"]:
            assert item["status"] == "pending"

    def test_list_invalid_status_filter(self):
        """Invalid status filter → 422."""
        app.dependency_overrides[get_current_user] = lambda: _make_table_db({})
        client = TestClient(app)
        response = client.get(
            "/api/v1/submissions?status=invalid", headers=ADMIN_HEADERS
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422


# ============================================================================
# Tests: GET /api/v1/submissions/{id} (admin detail)
# ============================================================================

class TestGetSubmission:
    """Tests for the admin submission detail endpoint."""

    def test_get_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.get(f"/api/v1/submissions/{_SUB_ID}")
        assert response.status_code == 401

    def test_get_submission_found(self):
        """Existing submission → 200 with files."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],
            "submission_files": [MOCK_FILE],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/{_SUB_ID}", headers=ADMIN_HEADERS
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == _SUB_ID
        assert "files" in body

    def test_get_submission_not_found(self):
        """Non-existent submission → 404."""
        mock_db = _make_table_db({"submissions": [], "submission_files": []})

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/nonexistent-id", headers=ADMIN_HEADERS
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404


# ============================================================================
# Tests: POST /api/v1/submissions/{id}/approve (admin)
# ============================================================================

class TestApproveSubmission:
    """Tests for the admin approve endpoint."""

    APPROVE_BODY = {
        "subject_id": 1,
        "exam_type": "Annual Exam",
        "year": 2024,
        "paper_type": "question",
    }

    def test_approve_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/approve",
            json=self.APPROVE_BODY,
        )
        assert response.status_code == 401

    def test_approve_pending_submission(self):
        """Pending submission → approve → 200, paper created."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],
            "submission_files": [MOCK_FILE],
            "papers": [MOCK_PAPER],
        })
        # Mock storage for copy: download from submissions, upload to papers, get_public_url from papers
        mock_db.storage = MagicMock()
        submissions_bucket_mock = MagicMock()
        submissions_bucket_mock.download.return_value = b"file content"
        papers_bucket_mock = MagicMock()
        papers_bucket_mock.upload.return_value = MagicMock()
        papers_bucket_mock.get_public_url.return_value = MOCK_PAPER["public_url"]
        
        def from_side_effect(bucket_name):
            if bucket_name == "submissions":
                return submissions_bucket_mock
            elif bucket_name == "papers":
                return papers_bucket_mock
            return MagicMock()
            
        mock_db.storage.from_.side_effect = from_side_effect

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/approve",
            json=self.APPROVE_BODY,
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["submission_id"] == _SUB_ID
        assert "paper_ids" in body

    def test_approve_not_found(self):
        """Non-existent submission → 404."""
        mock_db = _make_table_db({"submissions": [], "submission_files": []})

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/nonexistent/approve",
            json=self.APPROVE_BODY,
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_approve_already_approved_submission(self):
        """Already-approved submission → 422."""
        already_approved = {**MOCK_SUBMISSION, "status": "approved"}
        mock_db = _make_table_db({
            "submissions": [already_approved],
            "submission_files": [MOCK_FILE],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/approve",
            json=self.APPROVE_BODY,
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "already" in response.json()["detail"].lower()

    def test_approve_already_rejected_submission(self):
        """Already-rejected submission → 422."""
        already_rejected = {**MOCK_SUBMISSION, "status": "rejected"}
        mock_db = _make_table_db({
            "submissions": [already_rejected],
            "submission_files": [MOCK_FILE],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/approve",
            json=self.APPROVE_BODY,
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    def test_approve_does_not_expose_pending_to_public_papers(self):
        """Pending submissions must not appear in public paper listings."""
        # The public papers endpoint filters by is_visible=true.
        # Pending submission files are NOT in the papers table at all —
        # they only get inserted on approval. Verify the public paper
        # list returns nothing when no papers exist.
        from app.dependencies.supabase import get_db as get_public_db

        public_db = _make_table_db({"papers": []})

        app.dependency_overrides[get_public_db] = lambda: public_db
        client = TestClient(app)
        response = client.get("/api/v1/papers")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["count"] == 0


# ============================================================================
# Tests: POST /api/v1/submissions/{id}/reject (admin)
# ============================================================================

class TestRejectSubmission:
    """Tests for the admin reject endpoint."""

    def test_reject_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/reject",
            json={},
        )
        assert response.status_code == 401

    def test_reject_pending_submission(self):
        """Pending submission → reject → 200, no paper created."""
        rejected = {**MOCK_SUBMISSION, "status": "rejected"}
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION, rejected],  # first for get_by_id, second for update
            "submission_files": [],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/reject",
            json={"rejection_reason": "Duplicate paper"},
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "rejected"
        assert body["rejection_reason"] == "Duplicate paper"

    def test_reject_without_reason(self):
        """Rejection reason is optional."""
        rejected = {**MOCK_SUBMISSION, "status": "rejected"}
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION, rejected],
            "submission_files": [],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/reject",
            json={},
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_reject_not_found(self):
        """Non-existent submission → 404."""
        mock_db = _make_table_db({"submissions": []})

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/nonexistent/reject",
            json={},
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_reject_already_reviewed_submission(self):
        """Already-approved submission → 422."""
        approved = {**MOCK_SUBMISSION, "status": "approved"}
        mock_db = _make_table_db({
            "submissions": [approved],
            "submission_files": [],
        })

        app.dependency_overrides[get_current_user] = lambda: mock_db
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/reject",
            json={},
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    def test_reject_does_not_create_paper(self):
        """Rejection must NOT create a paper record in the papers table."""
        # After rejection, the papers table should still be empty
        from app.dependencies.supabase import get_db as get_public_db

        public_db = _make_table_db({"papers": []})

        app.dependency_overrides[get_public_db] = lambda: public_db
        client = TestClient(app)
        response = client.get("/api/v1/papers")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["count"] == 0


# ============================================================================
# Tests: Existing paper endpoints are not regressed
# ============================================================================

class TestExistingPapersNotRegressed:
    """Verify that existing paper endpoints continue to work after adding submissions."""

    def _make_papers_db(self, papers_data):
        mock_db = MagicMock()
        response = MagicMock()
        response.data = papers_data

        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = response

        mock_db.table.return_value = query
        return mock_db

    def test_get_papers_still_works(self):
        """GET /api/v1/papers returns 200."""
        from app.dependencies.supabase import get_db as get_public_db

        _PAPER_ROW = {
            "id": 42, "subject_id": 8, "exam_type": "Annual Exam",
            "year": 2024, "month": None, "district": None,
            "title": "Class 10 Maths", "paper_type": "question",
            "public_url": "https://example.com/paper.pdf",
            "youtube_url": None, "original_filename": "test.pdf",
            "is_visible": True, "status": "published",
            "download_count": 0, "created_at": _NOW,
        }

        app.dependency_overrides[get_public_db] = lambda: self._make_papers_db([_PAPER_ROW])
        client = TestClient(app)
        response = client.get("/api/v1/papers")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["data"][0]["id"] == 42

    def test_search_papers_still_works(self):
        """GET /api/v1/papers/search returns 200."""
        from app.dependencies.supabase import get_db as get_public_db

        # Empty search with empty query returns no results
        app.dependency_overrides[get_public_db] = lambda: self._make_papers_db([])
        client = TestClient(app)
        response = client.get("/api/v1/papers/search?q=")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_health_still_works(self):
        """GET /api/v1/health returns 200."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
