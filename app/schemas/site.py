from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrackedPageIn(BaseModel):
    url: str
    page_label: str
    crawl_method: str = Field(default="http", pattern="^(http|playwright)$")
    crawl_interval_minutes: int = 720
    is_active: bool = True


class TrackedPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    url: str
    page_label: str
    crawl_method: str
    crawl_interval_minutes: int
    is_active: bool
    last_checked_at: datetime | None
    created_at: datetime


class SiteIn(BaseModel):
    name: str
    sector: str
    base_url: str
    is_active: bool = True
    tracked_pages: list[TrackedPageIn] = Field(default_factory=list)


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sector: str
    base_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SiteDetailOut(SiteOut):
    tracked_pages: list[TrackedPageOut] = Field(default_factory=list)
