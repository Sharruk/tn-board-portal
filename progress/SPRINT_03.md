# Sprint 03 — API Migration (Classes & Subjects)

> **Status:** COMPLETE  
> **Branch:** `dev`  
> **Architecture validated:** Route → Service → Repository → Supabase

---

## Goal

Implement the first real API endpoints backed by live Supabase data,
validating the clean architecture pipeline end-to-end.
No frontend files touched. No schema changes. No auth.

---

## Endpoints Implemented

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/classes` | List all 4 school classes with subject counts |
| GET | `/api/v1/classes/{id}` | Get one class (9, 10, 11, or 12) |
| GET | `/api/v1/subjects` | List all subjects (optional `?class_id=N` filter) |
| GET | `/api/v1/subjects/{id}` | Get one subject by id |

---

## Architecture Validated

```
HTTP Request
    │
    ▼
Route  (app/api/v1/endpoints/classes.py)
    │  FastAPI validates types. Route calls service. Returns model.
    ▼
Service  (app/services/classes_service.py)
    │  Business logic. Raises NotFoundError when needed.
    ▼
Repository  (app/repositories/classes_repository.py)
    │  Supabase query. Normalises nested PostgREST aggregate syntax.
    ▼
Supabase PostgreSQL
```

---

## Files Created

```
backend/app/
├── utils/
│   └── exceptions.py              ← Typed HTTPException subclasses
├── dependencies/
│   └── supabase.py                ← get_db() Depends() shim
├── schemas/
│   ├── class_.py                  ← ClassBase, ClassResponse, ClassListResponse
│   └── subject.py                 ← SubjectBase, SubjectResponse, SubjectListResponse
├── repositories/
│   ├── classes_repository.py      ← Supabase queries for `classes`
│   └── subjects_repository.py     ← Supabase queries for `subjects`
├── services/
│   ├── classes_service.py         ← Business logic for classes domain
│   └── subjects_service.py        ← Business logic for subjects domain
└── api/v1/
    ├── router.py                  ← [MODIFIED] registers classes + subjects routers
    └── endpoints/
        ├── classes.py             ← GET /classes, GET /classes/{id}
        └── subjects.py            ← GET /subjects, GET /subjects/{id}

backend/tests/
├── test_classes.py                ← 7 tests (mocked Supabase)
└── test_subjects.py               ← 8 tests (mocked Supabase)

progress/SPRINT_03.md             ← this file
```

---

## Sample JSON Responses

### GET /api/v1/classes

```json
{
  "data": [
    {"id": 9,  "name": "Class 9",  "slug": "9",  "subject_count": 5},
    {"id": 10, "name": "Class 10", "slug": "10", "subject_count": 5},
    {"id": 11, "name": "Class 11", "slug": "11", "subject_count": 11},
    {"id": 12, "name": "Class 12", "slug": "12", "subject_count": 11}
  ],
  "count": 4
}
```

### GET /api/v1/classes/10

```json
{
  "id": 10,
  "name": "Class 10",
  "slug": "10",
  "subject_count": 5
}
```

### GET /api/v1/classes/99 (not found)

```json
{
  "detail": "Class with id '99' was not found."
}
```

### GET /api/v1/subjects?class_id=10

```json
{
  "data": [
    {
      "id": 6,  "class_id": 10, "name": "Tamil",        "slug": "tamil",
      "is_practical": false, "display_order": 1,
      "class_name": "Class 10", "class_slug": "10", "paper_count": 8
    },
    {
      "id": 7,  "class_id": 10, "name": "English",      "slug": "english",
      "is_practical": false, "display_order": 2,
      "class_name": "Class 10", "class_slug": "10", "paper_count": 6
    },
    {
      "id": 8,  "class_id": 10, "name": "Mathematics",  "slug": "maths",
      "is_practical": false, "display_order": 3,
      "class_name": "Class 10", "class_slug": "10", "paper_count": 12
    },
    {
      "id": 9,  "class_id": 10, "name": "Science",      "slug": "science",
      "is_practical": true,  "display_order": 4,
      "class_name": "Class 10", "class_slug": "10", "paper_count": 5
    },
    {
      "id": 10, "class_id": 10, "name": "Social Science","slug": "social",
      "is_practical": false, "display_order": 5,
      "class_name": "Class 10", "class_slug": "10", "paper_count": 3
    }
  ],
  "count": 5,
  "class_id": 10
}
```

### GET /api/v1/subjects/8

```json
{
  "id": 8,
  "class_id": 10,
  "name": "Mathematics",
  "slug": "maths",
  "is_practical": false,
  "display_order": 3,
  "class_name": "Class 10",
  "class_slug": "10",
  "paper_count": 12
}
```

### GET /api/v1/subjects/9999 (not found)

```json
{
  "detail": "Subject with id '9999' was not found."
}
```

---

## Manual Testing Commands

```bash
# Start the server (backend/.env must have real Supabase credentials)
cd backend
uvicorn app.main:app --reload --port 8000

# Classes
curl http://localhost:8000/api/v1/classes
curl http://localhost:8000/api/v1/classes/10
curl http://localhost:8000/api/v1/classes/99     # → 404

# Subjects
curl http://localhost:8000/api/v1/subjects
curl http://localhost:8000/api/v1/subjects?class_id=10
curl http://localhost:8000/api/v1/subjects?class_id=11
curl http://localhost:8000/api/v1/subjects/8
curl http://localhost:8000/api/v1/subjects/9999  # → 404

# Swagger UI (interactive)
open http://localhost:8000/docs
```

### PowerShell equivalents

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/classes" | ConvertTo-Json -Depth 5
Invoke-RestMethod "http://localhost:8000/api/v1/classes/10" | ConvertTo-Json
Invoke-RestMethod "http://localhost:8000/api/v1/subjects?class_id=10" | ConvertTo-Json -Depth 5
Invoke-RestMethod "http://localhost:8000/api/v1/subjects/8" | ConvertTo-Json
```

---

## Running Tests

```bash
cd backend
pip install pytest
python -m pytest tests/ -v

# Expected output:
# tests/test_health.py::test_health_returns_200            PASSED
# tests/test_health.py::test_health_response_body          PASSED
# tests/test_health.py::test_root_returns_200              PASSED
# tests/test_health.py::test_root_response_body            PASSED
# tests/test_health.py::test_docs_available                PASSED
# tests/test_classes.py::test_list_classes_status_200      PASSED
# tests/test_classes.py::test_list_classes_count           PASSED
# tests/test_classes.py::test_list_classes_structure       PASSED
# tests/test_classes.py::test_list_classes_subject_...     PASSED
# tests/test_classes.py::test_get_class_10_status_200      PASSED
# tests/test_classes.py::test_get_class_not_found_...      PASSED
# tests/test_classes.py::test_get_class_response_fields... PASSED
# tests/test_subjects.py::...  (8 tests)                   PASSED
```

---

## Design Decisions

### Why `class_.py` (with underscore)?
`class` is a Python reserved keyword. The file is named `class_.py` to avoid shadowing it.

### Why `Depends(get_db)` instead of importing the singleton directly?
Using FastAPI's `Depends()` makes the database layer overridable in tests via `app.dependency_overrides[get_db]`. This is how all 15 new tests mock Supabase without touching production code.

### Why is `subject_count` in ClassResponse but not in `classes` table?
It's a computed aggregate (`subjects(count)`) from Supabase PostgREST. The repository normalises it. This mirrors exactly what `frontend/src/services/classes.js` does.

### Why does `GET /api/v1/subjects` accept `?class_id` filter?
The frontend has two functions: `getSubjects()` (all) and `getSubjectsForClass(id)`. Instead of two endpoints, one endpoint with an optional query parameter covers both use cases cleanly.

---

## Verification

| Check | Result |
|---|---|
| Backend starts | ✅ |
| GET /api/v1/classes | ✅ |
| GET /api/v1/classes/{id} | ✅ |
| GET /api/v1/subjects | ✅ |
| GET /api/v1/subjects/{id} | ✅ |
| 404 handling | ✅ |
| All tests pass | ✅ |
| No frontend files modified | ✅ |
| git status clean | ✅ |

---

## Sprint 04 Roadmap

Sprint 04 should migrate the **Papers** domain — the core content resource.

### Recommended scope

1. `app/schemas/paper.py` — `PaperResponse`, `PaperListResponse`, `PaperSearchParams`
2. `app/repositories/papers_repository.py` — wraps the `search_papers()` Supabase RPC
3. `app/services/papers_service.py`
4. `app/api/v1/endpoints/papers.py`:
   - `GET /api/v1/papers` — paginated list with optional filters
   - `GET /api/v1/papers/{id}` — single paper detail
   - `GET /api/v1/papers/search` — delegates to `search_papers` RPC

5. `tests/test_papers.py`

**Do NOT start Sprint 04 without approval.**
