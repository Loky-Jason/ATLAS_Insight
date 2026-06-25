"""SQLAlchemy model — CourseProposal."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CourseProposal(Base):
    __tablename__ = "course_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON: [{"type": "RNCP", "label": "Titre RNCP 35148"}, ...]
    certification_suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON refs: list of course ids or market_course ids
    based_on: Mapped[str | None] = mapped_column(Text, nullable=True)
    # draft | proposed | exported
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
