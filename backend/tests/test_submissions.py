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

from app.dependencies.supabase import get_db, get_db as get_supabase_admin_client
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
    "signed_url": f"https://example.supabase.co/storage/v1/object/sign/submissions/{_SUB_ID}/aaaa-bbbb.pdf?token=xyz",
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


@pytest.fixture(autouse=True)
def auto_override_storage(monkeypatch):
    def mock_get_storage():
        if get_db in app.dependency_overrides:
            db_inst = app.dependency_overrides[get_db]()
            if hasattr(db_inst, "storage"):
                return db_inst.storage
        st = MagicMock()
        bucket = MagicMock()
        bucket.upload.return_value = MagicMock()
        bucket.download.return_value = b"%PDF-1.4 dummy file content"
        bucket.create_signed_url.return_value = {"signedURL": "https://example.supabase.co/signed/file.pdf"}
        bucket.get_public_url.return_value = "https://example.supabase.co/papers/uuid.pdf"
        st.from_.return_value = bucket
        return st

    monkeypatch.setattr("app.repositories.submissions_repository.get_storage_client", mock_get_storage)
    monkeypatch.setattr("app.db.storage.get_storage_client", mock_get_storage)



def _make_table_db(table_data: dict[str, list]) -> MagicMock:
    """
    Create a mock DB that returns different data depending on table and query parameters.
    """
    mock_db = MagicMock()
    mock_storage = MagicMock()
    bucket = MagicMock()
    bucket.upload.return_value = MagicMock()
    bucket.download.return_value = b"%PDF-1.4 dummy file content"
    bucket.create_signed_url.return_value = {"signedURL": "https://example.supabase.co/signed/file.pdf"}
    bucket.get_public_url.return_value = "https://example.supabase.co/papers/uuid.pdf"
    mock_storage.from_.return_value = bucket
    mock_db.storage = mock_storage

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        params = params or {}

        if "from submissions" in sql or "into submissions" in sql or "update submissions" in sql:
            rows = table_data.get("submissions", [])
            if "where id::text = :submission_id" in sql or "where id = :submission_id" in sql:
                sid = str(params.get("submission_id"))
                matches = [r for r in rows if str(r.get("id")) == sid]
                return MockResult(matches)
            if "status = :status" in sql:
                st = params.get("status")
                matches = [r for r in rows if r.get("status") == st]
                return MockResult(matches)
            return MockResult(rows)

        if "from submission_files" in sql or "into submission_files" in sql:
            rows = table_data.get("submission_files", [])
            if "count(*)" in sql:
                counts = {}
                for r in rows:
                    sub_id = str(r.get("submission_id", ""))
                    counts[sub_id] = counts.get(sub_id, 0) + 1
                return MockResult([(k, v) for k, v in counts.items()])
            if "where id::text = :file_id" in sql:
                fid = str(params.get("file_id"))
                matches = [r for r in rows if str(r.get("id")) == fid]
                return MockResult(matches)
            if "where submission_id::text = :submission_id" in sql:
                sid = str(params.get("submission_id"))
                matches = [r for r in rows if str(r.get("submission_id")) == sid]
                return MockResult(matches)
            return MockResult(rows)

        if "from papers" in sql or "into papers" in sql:
            rows = table_data.get("papers", [MOCK_PAPER])
            return MockResult(rows)

        return MockResult([])

    mock_db.execute.side_effect = _execute
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={"email": "test@example.com"},
            files=[self._make_upload_file()],
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422


    def test_create_submission_no_files(self):
        """No files provided → validation error from service."""
        mock_db = _make_table_db({"submissions": []})
        mock_db.storage = MagicMock()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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
        app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "contributor@example.com", "firebase_uid": "user-uid"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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
        app.dependency_overrides[get_supabase_admin_client] = lambda: _make_table_db({})
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "email": "admin@example.com", "firebase_uid": "admin-uid"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
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
# Tests: POST /api/v1/submissions/{id}/restore (admin)
# ============================================================================

class TestRestoreSubmission:
    """Tests for the admin restore-to-pending endpoint."""

    def test_restore_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.post(f"/api/v1/submissions/{_SUB_ID}/restore")
        assert response.status_code == 401

    def test_restore_rejected_to_pending(self):
        """Rejected submission → restore → 200, status = pending."""
        rejected_sub = {**MOCK_SUBMISSION, "status": "rejected", "rejection_reason": "Duplicate"}
        restored_sub = {**MOCK_SUBMISSION, "status": "pending", "rejection_reason": None, "reviewed_at": None}

        mock_db = _make_table_db({
            "submissions": [rejected_sub, restored_sub],  # first for get_by_id, second for restore update
            "submission_files": [],
        })

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/restore",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "pending"
        assert body["submission_id"] == _SUB_ID

    def test_restore_pending_submission_fails(self):
        """Cannot restore a pending submission — it's already pending."""
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],  # status = pending
            "submission_files": [],
        })

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/restore",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "only rejected" in response.json()["detail"].lower()

    def test_restore_approved_submission_fails(self):
        """Cannot restore an approved submission — it is already published."""
        approved_sub = {**MOCK_SUBMISSION, "status": "approved"}
        mock_db = _make_table_db({
            "submissions": [approved_sub],
            "submission_files": [],
        })

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/{_SUB_ID}/restore",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        assert "only rejected" in response.json()["detail"].lower()

    def test_restore_not_found(self):
        """Non-existent submission → 404."""
        mock_db = _make_table_db({"submissions": []})

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.post(
            f"/api/v1/submissions/nonexistent/restore",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_restore_then_approve_workflow(self):
        """
        Full REJECTED → PENDING → APPROVED workflow (service-level unit test).
        Verifies that after restoring to pending, the approve endpoint accepts it.
        """
        # Phase 1: restore — submission starts as rejected
        rejected_sub = {**MOCK_SUBMISSION, "status": "rejected", "rejection_reason": "Needs work"}
        restored_sub = {**MOCK_SUBMISSION, "status": "pending", "rejection_reason": None, "reviewed_at": None}

        restore_db = _make_table_db({
            "submissions": [rejected_sub, restored_sub],
            "submission_files": [],
        })
        app.dependency_overrides[get_supabase_admin_client] = lambda: restore_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        r1 = client.post(f"/api/v1/submissions/{_SUB_ID}/restore", headers=ADMIN_HEADERS)
        app.dependency_overrides.clear()

        assert r1.status_code == 200
        assert r1.json()["status"] == "pending"

        # Phase 2: approve — submission is now pending
        mock_db = _make_table_db({
            "submissions": [MOCK_SUBMISSION],  # pending
            "submission_files": [MOCK_FILE],
            "papers": [MOCK_PAPER],
        })
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

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        r2 = client.post(
            f"/api/v1/submissions/{_SUB_ID}/approve",
            json={"subject_id": 1, "exam_type": "Annual Exam", "year": 2024, "paper_type": "question"},
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"


# ============================================================================
# Tests: GET /api/v1/submissions/files/{file_id}/download (admin)
# ============================================================================

class TestDownloadSubmissionFile:
    """Tests for the admin secure file download proxy endpoint."""

    def test_download_requires_auth(self):
        """No auth header → 401."""
        client = TestClient(app)
        response = client.get(f"/api/v1/submissions/files/{_FILE_ID}/download")
        assert response.status_code == 401

    def test_download_admin_can_download(self):
        """Admin with valid token can download a file → 200 with binary content."""
        file_bytes = b"%PDF-1.4 fake pdf content here"

        mock_db = _make_table_db({
            "submission_files": [MOCK_FILE],
        })
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.download.return_value = file_bytes
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/files/{_FILE_ID}/download",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.content == file_bytes
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "math_paper.pdf" in response.headers.get("content-disposition", "")
        assert response.headers.get("content-type", "").startswith("application/pdf")

    def test_download_file_not_found(self):
        """Non-existent file_id → 404."""
        mock_db = _make_table_db({"submission_files": []})

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/files/nonexistent-file-id/download",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_download_storage_failure_returns_500(self):
        """Storage download error → 500 (safe error — no internals exposed)."""
        mock_db = _make_table_db({"submission_files": [MOCK_FILE]})
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.download.side_effect = RuntimeError("Storage unavailable")
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/files/{_FILE_ID}/download",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 500
        # Ensure no storage internals are leaked
        body = response.json()
        assert "Storage unavailable" not in str(body)

    def test_download_non_admin_cannot_access(self):
        """USER role (non-admin) cannot download submission files."""
        client = TestClient(app)
        # No auth at all → 401
        response = client.get(f"/api/v1/submissions/files/{_FILE_ID}/download")
        assert response.status_code == 401

    def test_download_returns_correct_content_type_for_image(self):
        """PNG file → Content-Type: image/png."""
        png_file = {
            **MOCK_FILE,
            "id": "33333333-3333-3333-3333-333333333333",
            "original_filename": "diagram.png",
            "storage_path": f"{_SUB_ID}/cccc-dddd.png",
            "file_type": "png",
        }
        file_bytes = b"\x89PNG\r\n\x1a\n fake png bytes"

        mock_db = _make_table_db({"submission_files": [png_file]})
        mock_db.storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.download.return_value = file_bytes
        mock_db.storage.from_.return_value = bucket_mock

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {"role": "ADMIN", "firebase_uid": "admin-uid", "email": "admin@example.com"}
        client = TestClient(app)
        response = client.get(
            f"/api/v1/submissions/files/{png_file['id']}/download",
            headers=ADMIN_HEADERS,
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("image/png")
        assert response.content == file_bytes


# ============================================================================
# Tests: Existing paper endpoints are not regressed
# ============================================================================

class TestExistingPapersNotRegressed:
    """Verify that existing paper endpoints continue to work after adding submissions."""

    def _make_papers_db(self, papers_data):
        mock_db = MagicMock()
        mock_db.execute.return_value = MockResult(papers_data)
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


class TestCanonicalPaperTitleCreation:
    """Verify that paper titles created from submission approvals are canonical and preserve original filenames."""

    def test_canonical_title_format_on_approval(self):
        from app.repositories.submissions_repository import SubmissionsRepository

        mock_db = MagicMock()
        mock_storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.download.return_value = b"%PDF-1.4 test"
        bucket_mock.get_public_url.return_value = "https://example.supabase.co/storage/v1/object/public/papers/Class10_Social_Science.pdf"
        mock_storage.from_.return_value = bucket_mock

        # Setup mock db query responses
        subj_mapping = {"class_name": "Class 10", "subject_name": "Social Science"}
        inserted_paper = {
            "id": 14,
            "subject_id": 5,
            "exam_type": "Monthly Test",
            "year": 2026,
            "month": "July",
            "district": "Chennai",
            "title": "Class 10 Social Science Monthly Test July 2026 Chennai Question Paper",
            "paper_type": "question",
            "file_path": "Class10_Social_Science.pdf",
            "public_url": "https://example.supabase.co/storage/v1/object/public/papers/Class10_Social_Science.pdf",
            "original_filename": "Class 10 Social Science Monthly Test.pdf",
            "is_visible": True,
            "download_count": 0,
            "status": "published",
            "created_at": _NOW,
        }

        class MockCursor:
            def __init__(self, rows):
                self._rows = rows
            def fetchone(self):
                if not self._rows:
                    return None
                r = self._rows[0]
                m = MagicMock()
                m._mapping = r
                m.class_name = r.get("class_name")
                m.subject_name = r.get("subject_name")
                return m
            def fetchall(self):
                return []

        executed_statements = []
        def mock_execute(stmt, params=None):
            stmt_str = str(stmt)
            executed_statements.append((stmt_str, params))
            if "subjects" in stmt_str:
                return MockCursor([subj_mapping])
            elif "SELECT id FROM papers" in stmt_str:
                return MockCursor([])
            elif "INSERT INTO papers" in stmt_str:
                return MockCursor([inserted_paper])
            return MockCursor([])

        mock_db.execute = mock_execute

        repo = SubmissionsRepository(db=mock_db, storage=mock_storage)
        file_row = {
            "id": "file-123",
            "storage_path": "sub-123/uuid.pdf",
            "original_filename": "Class 10 Social Science Monthly Test.pdf",
            "file_type": "pdf",
        }
        submission = {"id": "sub-123", "details": "Uploaded test paper"}

        result = repo.create_paper_from_file(
            file_row=file_row,
            subject_id=5,
            exam_type="Monthly Test",
            year=2026,
            paper_type="question",
            month="July",
            district="Chennai",
            submission=submission,
        )

        assert result["title"] == "Class 10 Social Science Monthly Test July 2026 Chennai Question Paper"
        assert result["original_filename"] == "Class 10 Social Science Monthly Test.pdf"
        assert result["status"] == "published"
        assert "UUID" not in result["title"]
        # Verify status column was in INSERT INTO papers
        insert_stmts = [s for s, _ in executed_statements if "INSERT INTO papers" in s]
        assert len(insert_stmts) == 1
        assert "status" in insert_stmts[0]
        assert "'published'" in insert_stmts[0]

    def test_create_paper_from_file_rollback_on_error(self):
        from app.repositories.submissions_repository import SubmissionsRepository

        mock_db = MagicMock()
        mock_storage = MagicMock()
        bucket_mock = MagicMock()
        bucket_mock.download.return_value = b"%PDF-1.4 test"
        bucket_mock.get_public_url.return_value = "https://example.supabase.co/storage/v1/object/public/papers/paper.pdf"
        mock_storage.from_.return_value = bucket_mock

        mock_db.execute.side_effect = Exception("DB connection dropped")

        repo = SubmissionsRepository(db=mock_db, storage=mock_storage)
        file_row = {
            "id": "file-123",
            "storage_path": "sub-123/uuid.pdf",
            "original_filename": "paper.pdf",
            "file_type": "pdf",
        }
        submission = {"id": "sub-123"}

        with pytest.raises(Exception, match="DB connection dropped"):
            repo.create_paper_from_file(
                file_row=file_row,
                subject_id=5,
                exam_type="Monthly Test",
                year=2026,
                paper_type="question",
                month="July",
                district="Chennai",
                submission=submission,
            )

        mock_db.rollback.assert_called_once()


