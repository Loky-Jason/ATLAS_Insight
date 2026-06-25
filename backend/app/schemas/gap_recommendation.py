"""Pydantic v2 schemas — GapRecommendation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_RECOMMENDATION_TYPES = {"closure", "creation"}
_STATUSES = {"draft", "approved", "rejected", "implemented"}


class GapRecommendationCreate(BaseModel):
    recommendation_type: str = Field(min_length=1)
    scap_course_id: int | None = None
    market_course_id: int | None = None
    score: float = Field(ge=0.0, le=100.0)
    score_breakdown: str | None = None
    schools_offering: str | None = None
    suggested_hours: float | None = None
    certification_suggestions: str | None = None
    rationale: str | None = None
    status: str = Field(default="draft")

    @field_validator("recommendation_type")
    @classmethod
    def validate_recommendation_type(cls, v: str) -> str:
        if v not in _RECOMMENDATION_TYPES:
            msg = f"recommendation_type must be one of {_RECOMMENDATION_TYPES}"
            raise ValueError(msg)
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _STATUSES:
            msg = f"status must be one of {_STATUSES}"
            raise ValueError(msg)
        return v


class GapRecommendationUpdate(BaseModel):
    recommendation_type: str | None = Field(default=None, min_length=1)
    scap_course_id: int | None = None
    market_course_id: int | None = None
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    score_breakdown: str | None = None
    schools_offering: str | None = None
    suggested_hours: float | None = None
    certification_suggestions: str | None = None
    rationale: str | None = None
    status: str | None = None

    @field_validator("recommendation_type")
    @classmethod
    def validate_recommendation_type(cls, v: str) -> str:
        if v is not None and v not in _RECOMMENDATION_TYPES:
            msg = f"recommendation_type must be one of {_RECOMMENDATION_TYPES}"
            raise ValueError(msg)
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v is not None and v not in _STATUSES:
            msg = f"status must be one of {_STATUSES}"
            raise ValueError(msg)
        return v


class GapRecommendationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    recommendation_type: str
    scap_course_id: int | None
    market_course_id: int | None
    score: float
    score_breakdown: str | None
    schools_offering: str | None
    suggested_hours: float | None
    certification_suggestions: str | None
    rationale: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None


class GapRecommendationList(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    recommendation_type: str
    score: float
    status: str
    rationale: str | None
    created_at: datetime
