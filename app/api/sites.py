from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.auth import require_admin_auth
from app.models import Site, TrackedPage
from app.schemas.site import SiteDetailOut, SiteIn, SiteOut

router = APIRouter(tags=["sites"])


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "site"


@router.get("/sites", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).order_by(Site.name).all()


@router.get("/sites/{site_id}", response_model=SiteDetailOut)
def get_site(site_id: int, db: Session = Depends(get_db)):
    site = db.query(Site).options(joinedload(Site.tracked_pages)).filter(Site.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return site


@router.post("/sites", response_model=SiteDetailOut, status_code=201)
def create_site(
    payload: SiteIn, db: Session = Depends(get_db), _user: str = Depends(require_admin_auth)
):
    base_slug = slugify(payload.name)
    slug = base_slug
    suffix = 1
    while db.query(Site).filter(Site.slug == slug).first() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    site = Site(
        name=payload.name,
        slug=slug,
        sector=payload.sector,
        base_url=payload.base_url,
        is_active=payload.is_active,
    )
    db.add(site)
    db.flush()

    for tp in payload.tracked_pages:
        db.add(
            TrackedPage(
                site_id=site.id,
                url=tp.url,
                page_label=tp.page_label,
                crawl_method=tp.crawl_method,
                crawl_interval_minutes=tp.crawl_interval_minutes,
                is_active=tp.is_active,
            )
        )

    db.commit()
    db.refresh(site)
    return site
