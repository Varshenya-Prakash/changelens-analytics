from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.tracked_page import TrackedPage


class Snapshot(Base):
    """A single point-in-time capture of a tracked page."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_page_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_pages.id", ondelete="CASCADE"), index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetch_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tracked_page: Mapped[TrackedPage] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Snapshot page={self.tracked_page_id} at={self.fetched_at}>"
