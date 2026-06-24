"""Pydantic v2 schemas — Favorite."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator
from typing import Self


class FavoriteCreate(BaseModel):
    course_id: int | None = None
    market_course_id: int | None = None

    @model_validator(mode="after")
    def check_exactly_one_fk(self) -> Self:
        """Exactement une des deux FK doit être renseignée."""
        has_course = self.course_id is not None
        has_market = self.market_course_id is not None
        if not has_course and not has_market:
            raise ValueError("course_id ou market_course_id doit être renseigné.")
        if has_course and has_market:
            raise ValueError("Un seul de course_id ou market_course_id doit être renseigné.")
        return self


class FavoriteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    course_id: int | None
    market_course_id: int | None
    created_at: datetime
