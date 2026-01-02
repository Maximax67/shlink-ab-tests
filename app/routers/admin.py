"""
Router for admin dashboard and A/B test management
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Form, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ShortUrl, ABTest
from app.schemas import (
    ABTestCreate,
    ABTestUpdate,
    ABTestResponse,
    ShortUrlWithTests,
)
from app.services.ab_test_service import ABTestService, ABTestValidationError
from app.services.auth_service import AuthService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


def verify_admin_session(
    admin_session: Optional[str] = Cookie(None, alias=settings.session_cookie_name)
) -> str:
    """
    Dependency to verify admin session

    Raises:
        HTTPException: If session invalid
    """
    if not admin_session or not AuthService.verify_session(admin_session):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return admin_session


# ==================== Authentication Routes ====================


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    """Display login page"""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(token: str = Form(...)) -> RedirectResponse:
    """
    Authenticate admin and create session

    Args:
        token: Admin token from form

    Returns:
        Redirect to dashboard with session cookie
    """
    if not AuthService.verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Create session
    session_token = AuthService.create_session()

    # Redirect to dashboard with cookie
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        max_age=settings.session_max_age,
        samesite="strict",
    )

    logger.info("Admin login successful")
    return response


@router.post("/logout")
async def logout(session: str = Depends(verify_admin_session)) -> RedirectResponse:
    """Logout admin and invalidate session"""
    AuthService.invalidate_session(session)

    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key=settings.session_cookie_name)

    logger.info("Admin logout")
    return response


# ==================== Dashboard Routes ====================


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    session: str = Depends(verify_admin_session),
    db: Session = Depends(get_db),
) -> Response:
    """
    Display admin dashboard with list of short URLs

    Args:
        request: FastAPI request
        page: Page number (1-indexed)
        limit: Items per page
        search: Search query for short_code or title
        session: Admin session token
        db: Database session

    Returns:
        HTML response with dashboard
    """
    # Build query
    settings = get_settings()
    app_url = str(settings.app_url).rstrip("/")
    query = select(ShortUrl).where(ShortUrl.original_url.startswith(app_url))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (ShortUrl.short_code.like(search_pattern))
            | (ShortUrl.title.like(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.execute(count_query).scalar()

    if total_count is None:
        total_count = 0

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(ShortUrl.date_created.desc()).offset(offset).limit(limit)

    short_urls = list(db.execute(query).scalars().all())

    # Enrich with A/B test data
    enriched_urls = []
    for url in short_urls:
        ab_tests = ABTestService(db).get_all_tests(url.id)
        total_prob = sum(t.probability for t in ab_tests if t.is_active)

        enriched_urls.append(
            ShortUrlWithTests(
                id=url.id,
                short_code=url.short_code,
                original_url=url.original_url,
                redirect_url=url.redirect_url,
                title=url.title,
                date_created=url.date_created,
                max_visits=url.max_visits,
                ab_tests=[ABTestResponse.model_validate(t) for t in ab_tests],
                total_probability=total_prob,
            )
        )

    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "short_urls": enriched_urls,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "search": search or "",
            "limit": limit,
        },
    )


@router.get("/short_url/{short_url_id}", response_class=HTMLResponse)
async def view_short_url(
    request: Request,
    short_url_id: int,
    session: str = Depends(verify_admin_session),
    db: Session = Depends(get_db),
) -> Response:
    """
    View detailed page for a short URL with A/B tests

    Args:
        request: FastAPI request
        short_url_id: ID of short URL
        session: Admin session token
        db: Database session

    Returns:
        HTML response with short URL details
    """
    short_url = db.get(ShortUrl, short_url_id)
    if not short_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    ab_tests = ABTestService(db).get_all_tests(short_url_id)
    total_prob = sum(t.probability for t in ab_tests if t.is_active)

    return templates.TemplateResponse(
        "short_url_detail.html",
        {
            "request": request,
            "short_url": short_url,
            "ab_tests": ab_tests,
            "total_probability": total_prob,
            "remaining_probability": max(0, 1.0 - total_prob),
        },
    )


# ==================== A/B Test CRUD Routes ====================


@router.post("/short_url/{short_url_id}/ab_test")
async def create_ab_test(
    short_url_id: int,
    target_url: str = Form(...),
    probability: float = Form(...),
    is_active: bool = Form(True),
    session: str = Depends(verify_admin_session),
    db: Session = Depends(get_db),
) -> Response:
    """
    Create a new A/B test

    Args:
        short_url_id: ID of short URL
        target_url: Target URL for variant
        probability: Probability (0.0-1.0)
        is_active: Whether test is active
        session: Admin session token
        db: Database session

    Returns:
        Redirect to short URL detail page
    """
    try:
        test_data = ABTestCreate(
            target_url=target_url, probability=probability, is_active=is_active
        )

        service = ABTestService(db)
        ab_test = service.create_test(short_url_id, test_data)

        logger.info(f"Created A/B test {ab_test.id} for short_url_id={short_url_id}")

        return RedirectResponse(
            url=f"/admin/short_url/{short_url_id}?success=Test created successfully",
            status_code=303,
        )
    except ABTestValidationError as e:
        logger.error(f"Failed to create A/B test: {e}")
        return RedirectResponse(
            url=f"/admin/short_url/{short_url_id}?error={str(e)}", status_code=303
        )


@router.post("/ab_test/{test_id}/update")
async def update_ab_test(
    test_id: int,
    target_url: Optional[str] = Form(None),
    probability: Optional[float] = Form(None),
    is_active: Optional[bool] = Form(None),
    session: str = Depends(verify_admin_session),
    db: Session = Depends(get_db),
) -> Response:
    """
    Update an existing A/B test

    Args:
        test_id: ID of A/B test
        target_url: New target URL (optional)
        probability: New probability (optional)
        is_active: New active status (optional)
        session: Admin session token
        db: Database session

    Returns:
        Redirect to short URL detail page
    """
    try:
        service = ABTestService(db)
        ab_test = service.get_test_by_id(test_id)

        if not ab_test:
            raise HTTPException(status_code=404, detail="A/B test not found")

        test_data = ABTestUpdate(
            target_url=target_url, probability=probability, is_active=is_active
        )

        ab_test = service.update_test(test_id, test_data)

        logger.info(f"Updated A/B test {test_id}")

        return RedirectResponse(
            url=f"/admin/short_url/{ab_test.short_url_id}?success=Test updated successfully",
            status_code=303,
        )
    except ABTestValidationError as e:
        logger.error(f"Failed to update A/B test: {e}")
        # Try to get short_url_id for redirect
        test = db.get(ABTest, test_id)
        short_url_id = test.short_url_id if test else 0
        return RedirectResponse(
            url=f"/admin/short_url/{short_url_id}?error={str(e)}", status_code=303
        )


@router.post("/ab_test/{test_id}/delete")
async def delete_ab_test(
    test_id: int,
    session: str = Depends(verify_admin_session),
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete an A/B test

    Args:
        test_id: ID of A/B test
        session: Admin session token
        db: Database session

    Returns:
        Redirect to short URL detail page
    """
    service = ABTestService(db)
    ab_test = service.get_test_by_id(test_id)

    if not ab_test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    short_url_id = ab_test.short_url_id

    if service.delete_test(test_id):
        logger.info(f"Deleted A/B test {test_id}")
        return RedirectResponse(
            url=f"/admin/short_url/{short_url_id}?success=Test deleted successfully",
            status_code=303,
        )
    else:
        return RedirectResponse(
            url=f"/admin/short_url/{short_url_id}?error=Failed to delete test",
            status_code=303,
        )
