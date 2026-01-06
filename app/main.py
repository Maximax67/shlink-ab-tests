"""
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import redirect, admin
from app.services.auth_service import AuthService
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Lifecycle events for the application"""
    logger.info("Starting URL Redirect & A/B Testing Service")
    logger.info(
        f"Database: {settings.database_url.split('@')[-1]}"
    )  # Log without credentials

    yield

    # Cleanup
    cleaned = AuthService.cleanup_revoked_tokens()
    logger.info(f"Shutting down. Cleaned up {cleaned} expired sessions")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="URL Redirect Service with A/B Testing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router, tags=["Admin"])
app.include_router(redirect.router, tags=["Redirect"])


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir), name="static")
