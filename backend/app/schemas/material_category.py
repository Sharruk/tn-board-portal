"""
Pydantic schemas for the Material Categories domain.
Supports hybrid category scoping (Global, Class-level, Subject-level).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MaterialCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Category name (e.g. Geometry, Formulas)")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the category")
    class_id: Optional[int] = Field(None, description="Class scope ID (None for global categories)")
    subject_id: Optional[int] = Field(None, description="Subject scope ID (None for class-wide or global categories)")
    display_order: int = Field(default=0, description="Sort order for UI rendering")
    is_active: bool = Field(default=True, description="Active status; inactive categories are hidden from new uploads")


class MaterialCategoryCreate(MaterialCategoryBase):
    slug: Optional[str] = Field(None, max_length=120, description="Optional explicit slug; auto-generated if omitted")


class MaterialCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class MaterialCategoryOut(MaterialCategoryBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    material_count: Optional[int] = Field(default=0, description="Count of published materials under this category")
    class_name: Optional[str] = Field(None, description="Joined name of parent class standard, if scoped")
    subject_name: Optional[str] = Field(None, description="Joined name of parent subject, if scoped")


class MaterialCategoryListResponse(BaseModel):
    data: list[MaterialCategoryOut]
    total: int
