"""Pydantic v2 schemas — SchoolCourse."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SchoolCourseCreate(BaseModel):
    school_registry_id: int
    external_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=512)
    url: str | None = None
    description: str | None = None
    duration_hours: float | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=255)
    format: str | None = Field(default=None, max_length=50)
    certification: str | None = Field(default=None, max_length=255)
    content_hash: str | None = Field(default=None, max_length=64)


class SchoolCourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    school_registry_id: int
    external_id: str
    title: str
    url: str | None
    description: str | None
    duration_hours: float | None
    price: float | None
    category: str | None
    format: str | None
    certification: str | None
    content_hash: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    last_updated_at: datetime | None
    is_removed: bool
    removed_at: datetime | None


class SchoolCourseList(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    school_registry_id: int
    external_id: str
    title: str
    url: str | None
    description: str | None
    duration_hours: float | None
    price: float | None
    category: str | None
    format: str | None
    certification: str | None
    content_hash: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    last_updated_at: datetime | None
    is_removed: bool
    removed_at: datetime | None
