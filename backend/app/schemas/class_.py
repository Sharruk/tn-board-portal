"""
Pydantic schemas for the Classes domain.

Schema hierarchy:
  ClassBase          — shared fields
  ClassResponse      — single class (GET /classes/{id})
  ClassListResponse  — paginated list (GET /classes)

Mirrors the Supabase `classes` table:
  id      INTEGER PRIMARY KEY   (9, 10, 11, 12)
  name    VARCHAR(20)           "Class 9" … "Class 12"
  slug    VARCHAR(10)           "9" … "12"

subject_count is a computed aggregate — not a column.
"""

from pydantic import BaseModel, Field


class ClassBase(BaseModel):
    id: int = Field(..., description="Class number (9, 10, 11, or 12)", examples=[10])
    name: str = Field(..., description="Human-readable class name", examples=["Class 10"])
    slug: str = Field(..., description="URL-safe identifier", examples=["10"])


class ClassResponse(ClassBase):
    """Single class with its subject count."""

    subject_count: int = Field(
        default=0,
        description="Number of subjects in this class",
        examples=[5],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 10,
                    "name": "Class 10",
                    "slug": "10",
                    "subject_count": 5,
                }
            ]
        }
    }


class ClassListResponse(BaseModel):
    """Paginated list of classes."""

    data: list[ClassResponse]
    count: int = Field(..., description="Total number of classes", examples=[4])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": [
                        {"id": 9, "name": "Class 9", "slug": "9", "subject_count": 5},
                        {"id": 10, "name": "Class 10", "slug": "10", "subject_count": 5},
                        {"id": 11, "name": "Class 11", "slug": "11", "subject_count": 11},
                        {"id": 12, "name": "Class 12", "slug": "12", "subject_count": 11},
                    ],
                    "count": 4,
                }
            ]
        }
    }
