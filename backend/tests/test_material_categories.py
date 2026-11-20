"""
Tests for Material Categories endpoints and service:
  - GET    /api/v1/material-categories
  - GET    /api/v1/admin/material-categories
  - POST   /api/v1/admin/material-categories
  - PUT    /api/v1/admin/material-categories/{id}
  - DELETE /api/v1/admin/material-categories/{id}
"""

import copy
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user, require_admin, require_role
from app.dependencies.supabase import get_db
from app.main import app
from app.repositories.material_categories_repository import MaterialCategoriesRepository
from app.services.material_categories_service import MaterialCategoriesService


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


SAMPLE_GLOBAL_CAT = {
    "id": 1,
    "class_id": None,
    "subject_id": None,
    "name": "Full Guides",
    "slug": "full-guides",
    "description": "Complete textbook solutions",
    "is_active": True,
    "display_order": 1,
    "created_at": "2026-11-20T10:00:00Z",
    "updated_at": "2026-11-20T10:00:00Z",
    "class_name": None,
    "subject_name": None,
    "material_count": 5,
}

SAMPLE_CLASS_CAT = {
    "id": 2,
    "class_id": 10,
    "subject_id": None,
    "name": "Class 10 General Guides",
    "slug": "class-10-general-guides",
    "description": "General revision for 10th",
    "is_active": True,
    "display_order": 2,
    "created_at": "2026-11-20T10:00:00Z",
    "updated_at": "2026-11-20T10:00:00Z",
    "class_name": "Class 10",
    "subject_name": None,
    "material_count": 2,
}

SAMPLE_SUBJECT_CAT = {
    "id": 3,
    "class_id": 10,
    "subject_id": 8,
    "name": "Geometry & Theorems",
    "slug": "geometry-theorems",
    "description": "Class 10 Maths geometry",
    "is_active": True,
    "display_order": 3,
    "created_at": "2026-11-20T10:00:00Z",
    "updated_at": "2026-11-20T10:00:00Z",
    "class_name": "Class 10",
    "subject_name": "Mathematics",
    "material_count": 4,
}


def _make_mock_db(categories=None):
    mock_db = MagicMock()
    cats = copy.deepcopy(categories or [SAMPLE_GLOBAL_CAT, SAMPLE_CLASS_CAT, SAMPLE_SUBJECT_CAT])

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        p = params or {}

        if "from classes" in sql:
            cid = p.get("class_id") or p.get("id")
            if cid in (9, 10, 11, 12):
                return MockResult([{"id": cid, "name": f"Class {cid}", "slug": str(cid)}])
            return MockResult([])

        if "from subjects" in sql:
            sid = p.get("subject_id") or p.get("id")
            if sid == 8:
                return MockResult([{"id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths"}])
            return MockResult([])

        if "select count(*)::int from study_materials where category_id" in sql:
            return MockResult(scalar_val=3)

        if ("where mc.id = :id" in sql or "where id = :id" in sql) and "update material_categories" not in sql and "delete from" not in sql:
            cid = p.get("id")
            match = next((c for c in cats if str(c["id"]) == str(cid)), None)
            return MockResult([dict(match)] if match else [])

        if "insert into material_categories" in sql:
            new_id = len(cats) + 1
            new_cat = {
                "id": new_id,
                "class_id": p.get("class_id"),
                "subject_id": p.get("subject_id"),
                "name": p.get("name"),
                "slug": p.get("slug"),
                "description": p.get("description"),
                "is_active": p.get("is_active", True),
                "display_order": p.get("display_order", 0),
                "created_at": "2026-11-20T10:00:00Z",
                "updated_at": "2026-11-20T10:00:00Z",
                "class_name": f"Class {p.get('class_id')}" if p.get("class_id") else None,
                "subject_name": "Mathematics" if p.get("subject_id") == 8 else None,
                "material_count": 0,
            }
            cats.append(new_cat)
            return MockResult([new_cat])

        if "where mc.slug = :slug" in sql or "where slug = :slug" in sql:
            slug_p = p.get("slug")
            cls_p = p.get("class_id")
            sub_p = p.get("subject_id")
            for c in cats:
                if c.get("slug") == slug_p:
                    c_cls = c.get("class_id")
                    c_sub = c.get("subject_id")
                    if c_cls == cls_p and c_sub == sub_p:
                        return MockResult([c])
            return MockResult([])

        if "update material_categories" in sql:
            cid = p.get("id")
            match = next((c for c in cats if str(c["id"]) == str(cid)), None)
            if match:
                if "name" in p: match["name"] = p["name"]
                if "description" in p: match["description"] = p["description"]
                if "is_active" in p: match["is_active"] = p["is_active"]
                if "is_active = true" in sql: match["is_active"] = True
                if "display_order" in p: match["display_order"] = p["display_order"]
                return MockResult([dict(match)])
            return MockResult([])

        if "lower(trim(" in sql:
            name_p = (p.get("name") or "").strip().lower()
            cls_p = p.get("class_id")
            sub_p = p.get("subject_id")
            for c in cats:
                if c["name"].strip().lower() == name_p:
                    c_cls = c.get("class_id")
                    c_sub = c.get("subject_id")
                    if c_cls == cls_p and c_sub == sub_p:
                        return MockResult([c])
            return MockResult([])

        if "select count(*)::int from study_materials sm" in sql or "from material_categories" in sql:
            return MockResult(cats)

        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


@pytest.fixture
def mock_admin():
    return {
        "id": "99999999-9999-9999-9999-999999999999",
        "firebase_uid": "admin_uid_123",
        "email": "admin@hungrylearner.com",
        "role": "ADMIN",
        "is_active": True,
    }


def test_public_list_categories():
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get("/api/v1/material-categories")
        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        assert len(data["data"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_admin_create_global_category(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "name": "Formula Sheets",
            "description": "Key formulas",
            "class_id": None,
            "subject_id": None,
            "display_order": 1,
            "is_active": True,
        }
        res = client.post("/api/v1/admin/material-categories", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Formula Sheets"
        assert data["class_id"] is None
        assert data["subject_id"] is None
    finally:
        app.dependency_overrides.clear()


def test_admin_create_subject_scoped_category(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "name": "Physics Derivations",
            "class_id": 10,
            "subject_id": 8,
            "display_order": 2,
        }
        res = client.post("/api/v1/admin/material-categories", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Physics Derivations"
        assert data["class_id"] == 10
        assert data["subject_id"] == 8
    finally:
        app.dependency_overrides.clear()


def test_reject_subject_category_without_parent_class(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "name": "Invalid Category",
            "class_id": None,
            "subject_id": 8,
        }
        res = client.post("/api/v1/admin/material-categories", json=payload)
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_category_soft_archival_when_materials_exist(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        res = client.delete("/api/v1/admin/material-categories/1")
        assert res.status_code == 200
        data = res.json()
        assert data["archived"] is True
        assert data["deleted"] is False
    finally:
        app.dependency_overrides.clear()


def test_reject_duplicate_category_in_same_scope(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        # SAMPLE_GLOBAL_CAT has name "Full Guides"
        payload = {
            "name": "full guides",  # case-insensitive test
            "class_id": None,
            "subject_id": None,
        }
        res = client.post("/api/v1/admin/material-categories", json=payload)
        assert res.status_code == 422
        assert "already exists for this scope" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_reactivate_archived_category(mock_admin):
    client = TestClient(app)
    archived_cat = dict(SAMPLE_GLOBAL_CAT)
    archived_cat["id"] = 99
    archived_cat["is_active"] = False
    mock_db = _make_mock_db([archived_cat])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        res = client.patch("/api/v1/admin/material-categories/99/reactivate")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True
    finally:
        app.dependency_overrides.clear()
