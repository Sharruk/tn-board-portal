# Sprint 04 — Papers Domain Migration

> **Status:** COMPLETE  
> **Branch:** `dev`  
> **Architecture:** Route → Service → Repository → Supabase RPC / PostgREST

---

## Goal

Migrate the Papers domain into FastAPI, preserving 100% of the existing
frontend behaviour while the Supabase JS client continues to work unchanged.

Zero SQL was written. All database access reuses existing Supabase RPCs
and PostgREST queries that were already proven by the frontend.

---

## Endpoints Implemented

| Method | Path | Frontend Equivalent |
|---|---|---|
| GET | `/api/v1/papers` | `getRecentPapers()` / `getPopularPapers()` |
| GET | `/api/v1/papers/search` | `searchPapers()` in `search.js` |
| GET | `/api/v1/papers/by-subject/{subject_id}` | `getPapersForSubject()` in `subjects.js` |
| GET | `/api/v1/papers/{id}` | `getPaper(id)` in `papers.js` |
| POST | `/api/v1/papers/{id}/download` | `recordDownload(id)` in `papers.js` |

---

## Supabase RPCs Wrapped (not recreated)

| RPC | Migration | Used by |
|---|---|---|
| `search_papers(q, p_class_id, p_exam_type, p_paper_type, p_month, p_district)` | 006, 007, 014, 016 | `/papers/search` |
| `increment_download_count(paper_id_param)` | 004, 007 | `/papers/{id}/download` |

---

## Files Created

```
backend/app/
├── schemas/
│   └── paper.py                   ← PaperBase, PaperResponse, PaperSummary,
│                                     PaperListResponse, PaperSearchResult, SearchResponse
├── repositories/
│   └── papers_repository.py       ← Supabase queries + RPC calls for papers
├── services/
│   └── papers_service.py          ← Business logic + _expand_terms() alias expansion
└── api/v1/
    ├── router.py                  ← [MODIFIED] registers papers router
    └── endpoints/
        └── papers.py              ← All 5 papers endpoints

backend/tests/
└── test_papers.py                 ← 24 tests (mocked Supabase)

progress/SPRINT_04.md              ← this file
```

---

## All Query Parameters

### GET /api/v1/papers

| Param | Type | Default | Description |
|---|---|---|---|
| `sort` | `recent` \| `popular` | `recent` | Sort order |
| `limit` | int | `10` | Max results (1–100) |

### GET /api/v1/papers/search

| Param | Type | Default | Description |
|---|---|---|---|
| `q` | string | `""` | Search term (empty → 0 results) |
| `class_id` | int | null | Filter by class (9–12) |
| `exam_type` | string | null | e.g. `Annual Exam`, `First Mid Term Test` |
| `paper_type` | string | null | `question` or `answer_key` |
| `month` | string | null | e.g. `July`, `November` |
| `district` | string | null | Partial match, e.g. `Chennai` |

### GET /api/v1/papers/by-subject/{subject_id}

| Param | Type | Default | Description |
|---|---|---|---|
| `exam_type` | string | null | Optional filter |
| `paper_type` | string | null | Optional filter |

---

## Example JSON Responses

### GET /api/v1/papers?sort=recent&limit=2

```json
{
  "data": [
    {
      "id": 42,
      "subject_id": 8,
      "exam_type": "Annual Exam",
      "year": 2024,
      "month": null,
      "district": null,
      "title": "Class 10 Maths Annual Exam 2024",
      "paper_type": "question",
      "public_url": "https://…/papers/uuid.pdf",
      "youtube_url": null,
      "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
      "status": "published",
      "download_count": 1234,
      "created_at": "2024-03-15T10:30:00Z"
    }
  ],
  "count": 1,
  "limit": 2
}
```

### GET /api/v1/papers/search?q=maths&class_id=10

```json
{
  "query": "maths",
  "total": 3,
  "results": [
    {
      "id": 42,
      "title": "Class 10 Maths Annual Exam 2024",
      "exam_type": "Annual Exam",
      "year": 2024,
      "month": null,
      "district": null,
      "paper_type": "question",
      "public_url": "https://…/papers/uuid.pdf",
      "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
      "subject_name": "Mathematics",
      "class_name": "Class 10",
      "class_id": 10,
      "status": "published",
      "download_count": 1234,
      "created_at": "2024-03-15T10:30:00Z"
    }
  ]
}
```

### GET /api/v1/papers/42

```json
{
  "id": 42,
  "subject_id": 8,
  "exam_type": "Annual Exam",
  "year": 2024,
  "month": null,
  "district": null,
  "title": "Class 10 Maths Annual Exam 2024",
  "paper_type": "question",
  "public_url": "https://…/papers/uuid.pdf",
  "youtube_url": null,
  "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
  "is_visible": true,
  "status": "published",
  "download_count": 1234,
  "created_at": "2024-03-15T10:30:00Z",
  "subject_name": "Mathematics",
  "subject_slug": "maths",
  "is_practical": false,
  "class_id": 10,
  "class_name": "Class 10",
  "class_slug": "10"
}
```

### GET /api/v1/papers/9999 (not found)

```json
{ "detail": "Paper with id '9999' was not found." }
```

### POST /api/v1/papers/42/download (success)

```
HTTP 204 No Content
```

---

## Example curl Commands

```bash
# Start server
cd backend
uvicorn app.main:app --reload --port 8000

# List 10 most recent published papers
curl "http://localhost:8000/api/v1/papers"

# List 5 most popular papers
curl "http://localhost:8000/api/v1/papers?sort=popular&limit=5"

# Full-text search (term expansion: maths → mathematics)
curl "http://localhost:8000/api/v1/papers/search?q=maths"

# Search with all filters
curl "http://localhost:8000/api/v1/papers/search?q=mathematics&class_id=10&exam_type=Annual+Exam&paper_type=question"

# Search with month + district (migration 016 columns)
curl "http://localhost:8000/api/v1/papers/search?q=tamil&month=July&district=Chennai"

# Papers for a specific subject (subject_id = 8 = Maths, Class 10)
curl "http://localhost:8000/api/v1/papers/by-subject/8"

# Papers for subject, filtered by exam type
curl "http://localhost:8000/api/v1/papers/by-subject/8?exam_type=Annual+Exam"

# Single paper detail
curl "http://localhost:8000/api/v1/papers/42"

# Paper not found → 404
curl "http://localhost:8000/api/v1/papers/9999"

# Record a download (increment counter)
curl -X POST "http://localhost:8000/api/v1/papers/42/download"

# PowerShell equivalents
Invoke-RestMethod "http://localhost:8000/api/v1/papers/search?q=maths&class_id=10" | ConvertTo-Json -Depth 4
Invoke-RestMethod "http://localhost:8000/api/v1/papers/42" | ConvertTo-Json
Invoke-RestMethod -Method POST "http://localhost:8000/api/v1/papers/42/download"
```

---

## Test Summary

```
tests/test_papers.py — 24 tests (all PASSED)

  List papers
  ✅ test_list_papers_status_200
  ✅ test_list_papers_response_structure
  ✅ test_list_papers_item_fields
  ✅ test_list_papers_popular_sort
  ✅ test_list_papers_empty

  Search
  ✅ test_search_papers_status_200
  ✅ test_search_papers_response_structure
  ✅ test_search_papers_result_fields
  ✅ test_search_papers_empty_query_returns_zero
  ✅ test_search_papers_with_all_filters
  ✅ test_search_deduplicates_by_id

  By subject
  ✅ test_list_by_subject_status_200
  ✅ test_list_by_subject_returns_list
  ✅ test_list_by_subject_empty

  Get single paper
  ✅ test_get_paper_status_200
  ✅ test_get_paper_response_fields
  ✅ test_get_paper_not_found_returns_404
  ✅ test_get_paper_all_fields_present

  Download
  ✅ test_record_download_status_204
  ✅ test_record_download_not_found_returns_404

  Term expansion (unit tests)
  ✅ test_term_expansion_maths
  ✅ test_term_expansion_no_expansion_for_full_word
  ✅ test_term_expansion_preserves_original
  ✅ test_term_expansion_empty_string

Total across all sprints:
  ======================== 45 passed in 1.25s ========================
```

---

## Design Decisions

### Why is `GET /papers/search` registered before `GET /papers/{id}`?

FastAPI matches routes in registration order. `search` is a literal string
that would be captured by `/{id}` (as `id = "search"`, failing int parse).
Registering explicit paths first avoids this collision. FastAPI's own
routing engine already handles this correctly (literal > parameter), but
explicit ordering is maintained for clarity.

### Why port `expandTerms()` to Python instead of calling it on the frontend?

The FastAPI `/papers/search` endpoint is a backend API — it must work
identically to the frontend service from any client (mobile apps, future
Android app, etc.). The `_expand_terms()` function in `papers_service.py`
is a direct Python port of the frontend's `expandTerms()` and produces
identical results.

### Why `POST /papers/{id}/download` instead of `GET`?

GET is idempotent (repeatable without side effects). Incrementing a counter
is a write operation with side effects — `POST` is semantically correct.
The frontend `recordDownload()` uses Supabase RPC which is effectively POST.

### Why is `file_path` excluded from all public responses?

`file_path` is an internal Supabase Storage key (a UUID path). Exposing
it to public clients would leak the storage bucket structure and allow
direct storage bypassing. The `public_url` field is the correct
publicly-accessible URL.

---

## Verification

| Check | Result |
|---|---|
| Backend starts | ✅ |
| All 45 tests pass | ✅ |
| No SQL written or duplicated | ✅ |
| RPCs called exactly as designed | ✅ |
| All 6 search filters preserved | ✅ |
| No frontend files modified | ✅ |
| `file_path` excluded from public responses | ✅ |
| `original_filename` included in responses | ✅ |
| `month`, `district` (migration 016) included | ✅ |
| `status` field used (not legacy `is_visible`) | ✅ |

---

## Sprint 05 Candidates

Suggested topics for Sprint 05 (awaiting approval):

1. **Constants endpoint** — `GET /api/v1/papers/constants` — returns `EXAM_TYPES`, `MONTHS`, `TN_DISTRICTS` so clients don't hard-code them.
2. **Notices domain** — migrate `searchNotices()`, `GET /api/v1/notices`, `GET /api/v1/notices/{id}`.
3. **Recent + Popular on homepage** — `GET /api/v1/papers?sort=recent` is already done; extend to serve the homepage section data.
4. **Deployment** — configure Render web service, set env vars, deploy `dev` → staging for live endpoint testing.

**Do NOT start Sprint 05 without approval.**
