"""
Router for handling URL redirects
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import UrlBuilder, RedirectService


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def redirect_short_url(
    request: Request, url: str = Query(...), db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Handle redirect for short code with A/B testing

    Args:
        url: The URL parameter to redirect
        request: FastAPI request object
        db: Database session

    Returns:
        RedirectResponse to target URL

    Raises:
        HTTPException: If short code not found
    """
    service = RedirectService(db)

    # 1. Resolve URL
    short_url = service.resolve_url(url)
    if not short_url:
        logger.warning(f"URL not found: {url}")
        raise HTTPException(status_code=404, detail="URL not found")

    redirect_url = UrlBuilder.get_redirect_url(short_url.original_url)
    if not redirect_url:
        logger.warning(f"Redirect URL not found: {url}")
        raise HTTPException(status_code=404, detail="Redirect URL not found")

    # 2. Get IP address
    client_ip = request.client.host if request.client else "unknown"
    # Handle proxy headers
    if forwarded_for := request.headers.get("X-Forwarded-For"):
        client_ip = forwarded_for.split(",")[0].strip()
    elif real_ip := request.headers.get("X-Real-IP"):
        client_ip = real_ip

    # 3. Get last visit
    last_visit = service.get_last_visit(short_url.id)

    # 4. Get active A/B tests
    ab_tests = service.get_active_ab_tests(short_url.id)

    # 5. Select target URL (A/B variant or primary)
    target_url, ab_test_id = service.select_ab_variant(
        client_ip, ab_tests, redirect_url
    )

    # 6. Build final redirect URL with query params
    query_params = dict(request.query_params)
    del query_params["url"]

    final_url = UrlBuilder.build_url(
        target_url, True, query_params, last_visit, True, db
    )

    # 7. Log redirect
    logger.info(f"Redirecting {short_url.short_code} -> {final_url}")

    # 8. Redirect user
    return RedirectResponse(url=final_url, status_code=307)
