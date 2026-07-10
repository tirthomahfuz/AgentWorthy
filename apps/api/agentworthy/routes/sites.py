"""Authenticated site management routes."""

import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from agentworthy.auth import get_current_user, get_site_for_user
from agentworthy.database import get_db
from agentworthy.models import Scan, ScanStatus, Site, User
from agentworthy.schemas import SiteCreate, SiteResponse, SiteVerifyResponse
from agentworthy.services.verification import generate_verification_token, meta_tag_html, verify_ownership

router = APIRouter(prefix="/sites", tags=["sites"])


def normalize_root_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    return f"{parsed.scheme or 'https'}://{parsed.netloc}"


def site_to_response(site: Site, db: Session) -> SiteResponse:
    latest = (
        db.query(Scan)
        .filter(Scan.site_id == site.id, Scan.status == ScanStatus.COMPLETE)
        .order_by(desc(Scan.finished_at))
        .first()
    )
    return SiteResponse(
        id=site.id,
        root_url=site.root_url,
        display_name=site.display_name,
        verified=site.verified,
        verification_token=site.verification_token,
        created_at=site.created_at,
        latest_score=latest.overall_score if latest else None,
        latest_grade=latest.letter_grade if latest else None,
        last_scan_at=latest.finished_at if latest else None,
    )


@router.get("", response_model=list[SiteResponse])
def list_sites(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SiteResponse]:
    sites = db.query(Site).filter(Site.user_id == user.id).order_by(Site.created_at.desc()).all()
    return [site_to_response(s, db) for s in sites]


@router.post("", response_model=SiteResponse, status_code=201)
def create_site(
    body: SiteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteResponse:
    try:
        root_url = normalize_root_url(body.root_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing = db.query(Site).filter(Site.user_id == user.id, Site.root_url == root_url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Site already exists")

    site = Site(
        user_id=user.id,
        root_url=root_url,
        display_name=body.display_name,
        verified=False,
        verification_token=generate_verification_token(),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site_to_response(site, db)


@router.get("/{site_id}", response_model=SiteResponse)
def get_site(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteResponse:
    site = get_site_for_user(db, site_id, user)
    return site_to_response(site, db)


@router.post("/{site_id}/verify", response_model=SiteVerifyResponse)
def verify_site(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteVerifyResponse:
    site = get_site_for_user(db, site_id, user)
    if not site.verification_token:
        site.verification_token = generate_verification_token()
        db.commit()

    ok, message, methods = verify_ownership(site.root_url, site.verification_token)
    if ok:
        site.verified = True
        db.commit()
    return SiteVerifyResponse(verified=ok and site.verified, message=message, methods=methods)


@router.get("/{site_id}/verification-instructions")
def verification_instructions(
    site_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    site = get_site_for_user(db, site_id, user)
    if not site.verification_token:
        site.verification_token = generate_verification_token()
        db.commit()
    parsed = urlparse(site.root_url)
    return {
        "meta_tag": meta_tag_html(site.verification_token),
        "dns_txt_host": parsed.netloc,
        "dns_txt_value": f"agentworthy-verification={site.verification_token}",
    }
