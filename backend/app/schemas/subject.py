"""
Pydantic schemas for the Subjects domain.

Schema hierarchy:
  SubjectBase          — shared fields
  SubjectResponse      — single subject (GET /subjects/{id})
  SubjectListResponse  — list with optional class filter (GET /subjects)

Mirrors the Supabase `subjects` table:
  id             SERIAL PRIMARY KEY
  class_id       INTEGER FK → classes.id
  name           VARCHAR(100)
  slug           VARCHAR(50)
  is_practical   BOOLEAN
  display_order  INTEGER

Enriched fields (joined from related tables):
  class_name  — from classes.name
  class_slug  — from classes.slug
  paper_count — aggregate count from papers table
"""

from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    id: int = Field(..., description="Subject primary key", examples=[3])
    class_id: int = Field(..., description="Parent class ID (9–12)", examples=[10])
    name: str = Field(..., description="Subject name", examples=["Mathematics"])
    slug: str = Field(..., description="URL-safe slug, unique within class", examples=["maths"])
    is_practical: bool = Field(
        ..., description="True for lab/practical subjects", examples=[False]
    )
    display_order: int = Field(
        ..., description="Ascending display order within class", examples=[3]
    )


class SubjectResponse(SubjectBase):
    """Single subject with class info and paper count."""

    class_name: str | None = Field(
        default=None,
        description="Parent class name",
        examples=["Class 10"],
    )
    class_slug: str | None = Field(
        default=None,
        description="Parent class slug",
        examples=["10"],
    )
    paper_count: int = Field(
        default=0,
        description="Number of papers available for this subject",
        examples=[12],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 8,
                    "class_id": 10,
                    "name": "Mathematics",
                    "slug": "maths",
                    "is_practical": False,
                    "display_order": 3,
                    "class_name": "Class 10",
                    "class_slug": "10",
                    "paper_count": 12,
                }
            ]
        }
    }


class SubjectListResponse(BaseModel):
    """List of subjects, optionally filtered by class."""

    data: list[SubjectResponse]
    count: int = Field(..., description="Total subjects returned", examples=[5])
    class_id: int | None = Field(
        default=None,
        description="class_id filter applied, if any",
        examples=[10],
    )
