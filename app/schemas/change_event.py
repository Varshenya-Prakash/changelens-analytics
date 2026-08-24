from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryMatchOut(BaseModel):
    name: str
    confidence: float
    matched_terms: list[str]


class ChangeEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_page_id: int
    detected_at: datetime
    status: str
    primary_category: str
    signal_score: float
    signal_level: str
    is_cosmetic: bool
    diff_summary: str
    recommendation: str

    # Denormalized for convenience in list views.
    organization_name: str | None = None
    page_label: str | None = None
    page_url: str | None = None


class ChangeEventDetailOut(ChangeEventListItem):
    change_magnitude: float
    similarity_score: float
    added_text: str
    removed_text: str
    scoring_explanation: str
    category_matches: list[CategoryMatchOut] = Field(default_factory=list)
    source_url: str | None = None


class ChangeEventStatusUpdate(BaseModel):
    status: str = Field(pattern="^(new|reviewed|dismissed)$")
