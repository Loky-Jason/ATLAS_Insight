"""Pydantic v2 schemas — MarketScanRun."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketScanRunRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    school_registry_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    courses_found: int
    courses_new: int
    courses_removed: int
    courses_modified: int
    error_msg: str | None


class MarketScanRunList(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    school_registry_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    courses_found: int
    courses_new: int
    courses_removed: int
    courses_modified: int
    error_msg: str | None
