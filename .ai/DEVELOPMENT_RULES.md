# DEVELOPMENT_RULES.md — Engineering & Database Standards
# TN Board Portal

---

## 1. Database & Migration Rules

1. **Retain Migration History**:
   - Migration files `001_schema.sql` through `025_paper_description_and_fields.sql` represent the ordered schema history.
   - Never delete, reorder, or squash existing migrations.
2. **Forward Migrations Only**:
   - All new database changes must be introduced in a new incremental migration file (`026_...`).
   - Use `IF NOT EXISTS` / `IF EXISTS` for idempotent, non-breaking schema evolution.
3. **Resilient SQL Execution**:
   - Backend repositories must handle optional/new columns gracefully so unmigrated database instances do not fail with `UndefinedColumn` errors.
4. **Transaction Safety**:
   - Explicitly roll back sessions (`self._db.rollback()`) upon database exceptions before re-raising or falling back.

---

## 2. API & Backend Conventions

1. **Layer Separation**:
   - **Endpoints (`app/api/v1/endpoints/`)**: Route definition, dependency injection, and HTTP response handling.
   - **Services (`app/services/`)**: Business logic, input validation, and orchestration.
   - **Repositories (`app/repositories/`)**: Direct database access and storage manipulation.
   - **Schemas (`app/schemas/`)**: Pydantic models for request validation and response serialization.
2. **Error Handling**:
   - Raise standard FastAPI `HTTPException` with appropriate status codes (`400`, `401`, `403`, `404`, `500`).
   - Never leak internal stack traces or connection strings in HTTP response details.
3. **URL Routing**:
   - Backend endpoints are prefixed with `/api/v1/`.
   - Vercel same-origin routing maps `/api/*` to `api/index.py`.

---

## 3. Frontend Conventions

1. **API Client (`frontend/src/lib/api.js`)**:
   - Use `apiFetch` for backend API interactions.
   - Keep URLs same-origin relative (`/api/v1/...`) for Vercel production and preview deployments.
2. **Component Organization**:
   - Reusable UI in `frontend/src/components/`.
   - Page views in `frontend/src/pages/`.
   - Context providers in `frontend/src/contexts/`.
   - Domain services in `frontend/src/services/`.
3. **State & Build Hygiene**:
   - Validate with `npm.cmd run build` to ensure all JSX, dependencies, and imports bundle without warnings.
