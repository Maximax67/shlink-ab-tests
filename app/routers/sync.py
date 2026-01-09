"""
Data sync API router for Google Apps Script integration
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.config import get_settings
from app.models.short_url import ShortUrl
from app.models.visit import Visit
from app.models.visit_location import VisitLocation
from app.schemas import (
    ShortUrlSyncSchema,
    VisitWithLocationSchema,
    SyncResponse,
    VisitLocationSchema,
)

router = APIRouter(prefix="/sync")
settings = get_settings()


def verify_api_token(x_api_token: str = Header(...)) -> None:
    """Verify the API token"""
    if x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid api token")


@router.get("/short-urls", response_model=SyncResponse)
def sync_short_urls(
    limit: int = Query(500, ge=1, le=10000, description="Number of records to fetch"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_token),
) -> SyncResponse:
    """
    Fetch short URLs for sync with pagination

    Headers:
        X-Api-Token: API key for authentication
    """
    # Get total count
    total = db.query(ShortUrl).count()

    # Fetch paginated data
    short_urls = (
        db.query(ShortUrl).order_by(ShortUrl.id).offset(offset).limit(limit).all()
    )

    return SyncResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[ShortUrlSyncSchema.model_validate(url) for url in short_urls],
    )


@router.get("/visits", response_model=SyncResponse)
def sync_visits(
    limit: int = Query(500, ge=1, le=10000, description="Number of records to fetch"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    short_url_id: Optional[int] = Query(None, description="Filter by short URL ID"),
    min_id: Optional[int] = Query(
        None,
        description="Fetch visits with ID greater than this (for append-only sync)",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_token),
) -> SyncResponse:
    """
    Fetch visits with location data for sync

    This endpoint joins visits with visit_locations to return all data in one call.

    Headers:
        X-Api-Token: API key for authentication

    Query Parameters:
        limit: Number of records to return (default 500, max 10000)
        offset: Number of records to skip (default 0)
        short_url_id: Filter visits for a specific short URL
        min_id: Fetch only visits with ID > this value (for incremental sync)
    """
    # Build query with location joined
    query = db.query(Visit).options(joinedload(Visit.location))

    # Apply filters
    if short_url_id is not None:
        query = query.filter(Visit.short_url_id == short_url_id)

    if min_id is not None:
        query = query.filter(Visit.id > min_id)

    # Get total count with filters applied
    total = query.count()

    # Fetch paginated data ordered by ID for consistency
    visits = query.order_by(Visit.id).offset(offset).limit(limit).all()

    return SyncResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[VisitWithLocationSchema.model_validate(visit) for visit in visits],
    )


@router.get("/visit-locations", response_model=SyncResponse)
def sync_visit_locations(
    limit: int = Query(500, ge=1, le=10000, description="Number of records to fetch"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    min_id: Optional[int] = Query(
        None, description="Fetch locations with ID greater than this"
    ),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_token),
) -> SyncResponse:
    """
    Fetch visit locations for sync (if needed separately)

    Headers:
        X-Api-Token: API key for authentication
    """
    query = db.query(VisitLocation)

    if min_id is not None:
        query = query.filter(VisitLocation.id > min_id)

    total = query.count()

    locations = query.order_by(VisitLocation.id).offset(offset).limit(limit).all()

    return SyncResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[VisitLocationSchema.model_validate(loc) for loc in locations],
    )
