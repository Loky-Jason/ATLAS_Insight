"""Pydantic v2 schemas — Favorite."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class FavoriteCreate(BaseModel):
    course_id: int | None = None
    market_course_id: int | None = None

    @field_validator("course_id", "market_course_id")
    @classmethod
    def check_at_least_one(cls, v, info):
        values = info.data
        if values.get("course_id") is None and values.get("market_course_id") is None:
            raise ValueError("Au moins course_id ou market_course_id doit être renseigné.")
        return v


class FavoriteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    course_id: int | None
    market_course_id: int | None
    created_at: datetime
