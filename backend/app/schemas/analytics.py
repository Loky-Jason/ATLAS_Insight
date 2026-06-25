"""Pydantic v2 schemas — Analytics dashboard.

Verrouille le contrat de /analytics/popularity (front ↔ back).
"""

from __future__ import annotations

from pydantic import BaseModel


class PopularityEntry(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    category: str | None
    enrolled_count: int
    dropout_count: int
    popularity_score: float | None


class AnalyticsPopularity(BaseModel):
    most_popular: list[PopularityEntry]
    least_popular: list[PopularityEntry]
    total_courses: int
    total_enrolled: int
    total_dropouts: int
