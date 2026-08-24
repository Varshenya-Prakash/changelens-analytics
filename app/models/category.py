from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.change_event import ChangeEvent


class ChangeCategory(Base):
    """A business-relevant classification bucket for detected changes."""

    __tablename__ = "change_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    default_weight: Mapped[float] = mapped_column(Float, default=1.0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChangeCategory {self.name}>"


class ChangeEventCategory(Base):
    """Many-to-many link between a ChangeEvent and its matched categories."""

    __tablename__ = "change_event_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_event_id: Mapped[int] = mapped_column(
        ForeignKey("change_events.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("change_categories.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    matched_terms: Mapped[list] = mapped_column(JSON, default=list)

    change_event: Mapped[ChangeEvent] = relationship(back_populates="category_links")
    category: Mapped[ChangeCategory] = relationship()
