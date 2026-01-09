"""
Basic test suite for the application
Run with: pytest test_app.py -v
"""

import os

os.environ.setdefault("APP_URL", "http://testserver")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("API_TOKEN", "test-api-token")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("APP_SCRIPT_URL", "http://localhost/script")
os.environ.setdefault("APP_SCRIPT_API_KEY", "test-api-key")

from typing import Any, Generator
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings
from app.models import Base, ShortUrl, ABTest
from app.database import get_db
from app.main import app


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, Any, None]:
    """Create test database and tables"""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, Any, None]:
    """Create test client with test database"""

    def override_get_db() -> Generator[Session, Any, None]:
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_short_url(test_db: Session) -> ShortUrl:
    """Create a sample short URL"""
    settings = get_settings()
    app_url = str(settings.app_url).rstrip("/")
    short_url = ShortUrl(
        id=1,
        original_url=f"{app_url}/?url=https://example.com/original",
        short_code="test",
        date_created=datetime.now(timezone.utc),
        forward_query=True,
        title_was_auto_resolved=False,
        crawlable=False,
    )
    test_db.add(short_url)
    test_db.commit()
    test_db.refresh(short_url)

    return short_url


class TestRedirect:
    """Test redirect functionality"""

    def test_redirect_short_code_not_found(
        self,
        client: TestClient,
        sample_short_url: ShortUrl,
    ) -> None:
        """Test 404 for non-existent short code"""
        response = client.get(
            "/",
            params={"url": "https://nonexistent.com"},
        )
        assert response.status_code == 404

    def test_redirect_to_primary_url(
        self,
        client: TestClient,
        sample_short_url: ShortUrl,
    ) -> None:
        """Test redirect to primary URL when no A/B tests"""
        response = client.get(
            "/",
            params={"url": "https://example.com/original"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/original"

    def test_redirect_with_query_params(
        self,
        client: TestClient,
        sample_short_url: ShortUrl,
    ) -> None:
        """Test query parameter forwarding"""
        response = client.get(
            "/",
            params={"url": "https://example.com/original", "utm_source": "test"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "utm_source=test" in response.headers["location"]


class TestABTest:
    """Test A/B testing functionality"""

    def test_create_ab_test_validation(
        self, test_db: Session, sample_short_url: ShortUrl
    ) -> None:
        """Test A/B test creation with validation"""
        from app.services.ab_test_service import ABTestService
        from app.schemas import ABTestCreate

        service = ABTestService(test_db)

        # Create valid test
        test_data = ABTestCreate(
            target_url="https://example.com/variant-a", probability=0.5, is_active=True
        )
        ab_test = service.create_test(sample_short_url.id, test_data)

        assert ab_test.id is not None
        assert ab_test.probability == 0.5
        assert ab_test.is_active is True

    def test_probability_sum_validation(
        self, test_db: Session, sample_short_url: ShortUrl
    ) -> None:
        """Test that total probability cannot exceed 1.0"""
        from app.services.ab_test_service import ABTestService, ABTestValidationError
        from app.schemas import ABTestCreate

        service = ABTestService(test_db)

        # Create first test with 0.7 probability
        test1_data = ABTestCreate(
            target_url="https://example.com/variant-a", probability=0.7, is_active=True
        )
        service.create_test(sample_short_url.id, test1_data)

        # Try to create second test with 0.5 probability (would exceed 1.0)
        test2_data = ABTestCreate(
            target_url="https://example.com/variant-b", probability=0.5, is_active=True
        )

        with pytest.raises(ABTestValidationError):
            service.create_test(sample_short_url.id, test2_data)

    def test_update_ab_test(self, test_db: Session, sample_short_url: ShortUrl) -> None:
        """Test updating an A/B test"""
        from app.services.ab_test_service import ABTestService
        from app.schemas import ABTestCreate, ABTestUpdate

        service = ABTestService(test_db)

        # Create test
        target_url = "https://example.com/variant-a"
        test_data = ABTestCreate(target_url=target_url, probability=0.5, is_active=True)
        ab_test = service.create_test(sample_short_url.id, test_data)

        # Update test
        update_data = ABTestUpdate(
            target_url=target_url, probability=0.3, is_active=False
        )
        updated_test = service.update_test(ab_test.id, update_data)

        assert updated_test.probability == 0.3
        assert updated_test.is_active is False

    def test_delete_ab_test(self, test_db: Session, sample_short_url: ShortUrl) -> None:
        """Test deleting an A/B test"""
        from app.services.ab_test_service import ABTestService
        from app.schemas import ABTestCreate

        service = ABTestService(test_db)

        # Create test
        test_data = ABTestCreate(
            target_url="https://example.com/variant-a", probability=0.5, is_active=True
        )
        ab_test = service.create_test(sample_short_url.id, test_data)

        # Delete test
        result = service.delete_test(ab_test.id)
        assert result is True

        # Verify deletion
        deleted_test = service.get_test_by_id(ab_test.id)
        assert deleted_test is None


class TestAdminAuth:
    """Test admin authentication"""

    def test_admin_login_page(self, client: TestClient) -> None:
        response = client.get("/admin/login")
        assert response.status_code == 200
        assert b"Admin Login" in response.content

    def test_admin_dashboard_requires_auth(self, client: TestClient) -> None:
        """Test that dashboard requires authentication"""
        response = client.get("/admin/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert response.has_redirect_location


class TestRedirectService:
    """Test redirect service logic"""

    def test_deterministic_ab_selection(
        self, test_db: Session, sample_short_url: ShortUrl
    ) -> None:
        """Test that same IP always gets same variant"""
        from app.services.redirect_service import RedirectService

        service = RedirectService(test_db)

        # Create A/B tests
        ab_test1 = ABTest(
            short_url_id=sample_short_url.id,
            target_url="https://example.com/variant-a",
            probability=0.5,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(ab_test1)
        test_db.commit()

        # Test deterministic selection
        ip = "192.168.1.100"
        result1, _ = service.select_ab_variant(
            ip, [ab_test1], sample_short_url.original_url
        )
        result2, _ = service.select_ab_variant(
            ip, [ab_test1], sample_short_url.original_url
        )

        # Same IP should get same result
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
