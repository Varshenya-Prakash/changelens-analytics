from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class MonitoringRun(Base):
    """A batch execution of the monitoring pipeline (manual or scheduled)."""

    __tablename__ = "monitoring_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|completed|failed
    pages_attempted: Mapped[int] = mapped_column(Integer, default=0)
    pages_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MonitoringRun {self.id} {self.status}>"
