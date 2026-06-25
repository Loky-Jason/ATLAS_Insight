"""SQLAlchemy model — GapRecommendation (recommandation d'écart marché/offre)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.db import Base


class GapRecommendation(Base):
    __tablename__ = "gap_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recommendation_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    scap_course_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    market_course_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("market_courses.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    schools_offering: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    certification_suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    scap_course: Mapped["Course | None"] = relationship(backref=backref("gap_recommendations", viewonly=True))
    market_course: Mapped["MarketCourse | None"] = relationship(backref=backref("gap_recommendations", viewonly=True))
