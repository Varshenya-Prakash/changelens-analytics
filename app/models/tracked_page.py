from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.change_event import ChangeEvent
    from app.models.site import Site
    from app.models.snapshot import Snapshot


class TrackedPage(Base):
    """A specific URL belonging to a Site that is monitored for changes."""

    __tablename__ = "tracked_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_label: Mapped[str] = mapped_column(String(200), nullable=False)
    crawl_method: Mapped[str] = mapped_column(String(20), default="http")  # http | playwright
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=720)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    site: Mapped[Site] = relationship(back_populates="tracked_pages")
    snapshots: Mapped[list[Snapshot]] = relationship(
        back_populates="tracked_page", cascade="all, delete-orphan", order_by="Snapshot.fetched_at"
    )
    change_events: Mapped[list[ChangeEvent]] = relationship(
        back_populates="tracked_page", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrackedPage {self.page_label}>"
