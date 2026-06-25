"""SQLAlchemy model — MarketScanRun (historique des scans de veille marché)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class MarketScanRun(Base):
    __tablename__ = "market_scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    school_registry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("school_registries.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    courses_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    courses_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    courses_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    courses_modified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_msg: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    school_registry: Mapped["SchoolRegistry"] = relationship(back_populates="scan_runs")
