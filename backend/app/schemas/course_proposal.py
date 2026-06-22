"""Pydantic v2 schemas — CourseProposal."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CourseProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    hours_estimated: float | None = Field(default=None, ge=0)
    certification_suggestions: str | None = None  # JSON string
    based_on: str | None = None  # JSON string
    status: str = Field(default="draft", pattern=r"^(draft|proposed|exported)$")


class CourseProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    hours_estimated: float | None = Field(default=None, ge=0)
    certification_suggestions: str | None = None
    based_on: str | None = None
    status: str | None = Field(default=None, pattern=r"^(draft|proposed|exported)$")


class CourseProposalRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    description: str | None
    hours_estimated: float | None
    certification_suggestions: str | None
    based_on: str | None
    status: str
    created_at: datetime
