"""Pydantic v2 schemas — AuditLog."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int | None
    action: str
    target: str | None
    timestamp: datetime
