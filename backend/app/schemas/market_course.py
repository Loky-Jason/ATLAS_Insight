"""Pydantic v2 schemas — MarketCourse."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketCourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    school: str | None = None
    source_url: str | None = None
    summary: str | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    why_it_works: str | None = None
    related_scap_course_id: int | None = None
    status: str = Field(default="candidate", pattern=r"^(candidate|reviewed|adopted|rejected)$")


class MarketCourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    school: str | None = None
    source_url: str | None = None
    summary: str | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    why_it_works: str | None = None
    related_scap_course_id: int | None = None
    status: str | None = Field(
        default=None, pattern=r"^(candidate|reviewed|adopted|rejected)$"
    )


class MarketCourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    school: str | None
    source_url: str | None
    summary: str | None
    relevance_score: float | None
    why_it_works: str | None
    related_scap_course_id: int | None
    status: str
    discovered_at: datetime
