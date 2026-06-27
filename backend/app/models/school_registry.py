"""SQLAlchemy model — SchoolRegistry (écoles référencées pour le scrap)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.market_course import MarketCourse
    from app.models.market_scan_run import MarketScanRun
    from app.models.school_course import SchoolCourse


class SchoolRegistry(Base):
    __tablename__ = "school_registries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    scraper_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="stub")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scan_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    school_courses: Mapped[list[SchoolCourse]] = relationship(
        back_populates="school_registry", cascade="all, delete-orphan"
    )
    scan_runs: Mapped[list[MarketScanRun]] = relationship(
        back_populates="school_registry", cascade="all, delete-orphan"
    )
    market_courses: Mapped[list[MarketCourse]] = relationship(back_populates="school_registry")
