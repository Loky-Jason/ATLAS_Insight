"""SQLAlchemy model — Course (cours SCAP)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # active | archived
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dropout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # JSON string: {"18-30": 12, "31-50": 45, "51+": 10}
    age_brackets: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hours_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Calculated field; updated by analytics service
    popularity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="scap")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
