from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.category import ChangeEventCategory
    from app.models.snapshot import Snapshot
    from app.models.tracked_page import TrackedPage

SIGNAL_LEVELS = ("noise", "low", "medium", "high", "critical")
EVENT_STATUSES = ("new", "reviewed", "dismissed")


class ChangeEvent(Base):
    """A detected, meaningful difference between two consecutive snapshots."""

    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_page_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_pages.id", ondelete="CASCADE"), index=True
    )
    previous_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True
    )
    current_snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)

    change_magnitude: Mapped[float] = mapped_column(Float, default=0.0)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    added_text: Mapped[str] = mapped_column(Text, default="")
    removed_text: Mapped[str] = mapped_column(Text, default="")
    diff_summary: Mapped[str] = mapped_column(Text, default="")

    primary_category: Mapped[str] = mapped_column(String(100), default="Other", index=True)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    signal_level: Mapped[str] = mapped_column(String(20), default="noise", index=True)
    is_cosmetic: Mapped[bool] = mapped_column(Boolean, default=False)
    scoring_explanation: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    tracked_page: Mapped[TrackedPage] = relationship(back_populates="change_events")
    current_snapshot: Mapped[Snapshot] = relationship(foreign_keys=[current_snapshot_id])
    previous_snapshot: Mapped[Snapshot | None] = relationship(foreign_keys=[previous_snapshot_id])
    category_links: Mapped[list[ChangeEventCategory]] = relationship(
        back_populates="change_event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChangeEvent {self.id} {self.primary_category} {self.signal_level}>"
