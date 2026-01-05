"""
Service for handling URL redirects and A/B testing
"""

import hashlib
import logging
from typing import Optional, Tuple
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models import ShortUrl, Visit, ABTest
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedirectService:
    """Handles redirect logic and A/B testing"""

    def __init__(self, db: Session):
        self.db = db

    def resolve_url(
        self, url: str, domain_id: Optional[int] = None
    ) -> Optional[ShortUrl]:
        """
        Resolve original url to ShortUrl

        Args:
            url: The original url to resolve
            domain_id: Optional domain ID for multi-domain support

        Returns:
            ShortUrl object or None if not found
        """

        settings = get_settings()
        app_url = str(settings.app_url).rstrip("/")

        query = select(ShortUrl).where(
            ShortUrl.original_url.startswith(app_url),
            ShortUrl.original_url.icontains(url),
        )

        if domain_id is not None:
            query = query.where(ShortUrl.domain_id == domain_id)
        else:
            query = query.where(ShortUrl.domain_id.is_(None))

        result = self.db.execute(query).scalar_one_or_none()

        if result:
            logger.info(f"Resolved url={url} to short_url_id={result.id}")
        else:
            logger.warning(f"URL not found for: {url}")

        return result

    def resolve_short_code(
        self, short_code: str, domain_id: Optional[int] = None
    ) -> Optional[ShortUrl]:
        """
        Resolve short code to ShortUrl

        Args:
            short_code: The short code to resolve
            domain_id: Optional domain ID for multi-domain support

        Returns:
            ShortUrl object or None if not found
        """
        query = select(ShortUrl).where(ShortUrl.short_code == short_code)

        if domain_id is not None:
            query = query.where(ShortUrl.domain_id == domain_id)
        else:
            query = query.where(ShortUrl.domain_id.is_(None))

        result = self.db.execute(query).scalar_one_or_none()

        if result:
            logger.info(f"Resolved short_code={short_code} to short_url_id={result.id}")
        else:
            logger.warning(f"Short code not found: {short_code}")

        return result

    def get_last_visit(self, short_url_id: int) -> Optional[Visit]:
        """
        Get the most recent visit for a short URL

        Args:
            short_url_id: ID of the short URL

        Returns:
            Visit object or None if no visits exist
        """
        query = (
            select(Visit)
            .where(Visit.short_url_id == short_url_id)
            .order_by(desc(Visit.date))
            .limit(1)
        )

        return self.db.execute(query).scalar_one_or_none()

    def get_active_ab_tests(self, short_url_id: int) -> list[ABTest]:
        """
        Get all active A/B tests for a short URL

        Args:
            short_url_id: ID of the short URL

        Returns:
            List of active ABTest objects
        """
        query = (
            select(ABTest)
            .where(ABTest.short_url_id == short_url_id)
            .where(ABTest.is_active.is_(True))
            .order_by(ABTest.id)
        )

        return list(self.db.execute(query).scalars().all())

    def select_ab_variant(
        self, ip_address: str, ab_tests: list[ABTest], primary_url: str
    ) -> Tuple[str, Optional[int]]:
        """
        Deterministically select A/B test variant based on IP hash

        Args:
            ip_address: User's IP address
            ab_tests: List of active A/B tests
            primary_url: Primary URL (fallback)

        Returns:
            Tuple of (target_url, ab_test_id or None)
        """
        if not ab_tests:
            return primary_url, None

        # Create deterministic hash from IP
        to_hash = primary_url + ip_address
        hash_value = hashlib.md5(to_hash.encode()).hexdigest()
        hash_float = int(hash_value[:8], 16) / (16**8)

        # Select variant based on probability ranges
        cumulative_prob = 0.0
        for test in ab_tests:
            cumulative_prob += test.probability
            if hash_float < cumulative_prob:
                logger.info(f"Selected A/B test {test.id} for IP hash {hash_float:.4f}")
                return test.target_url, test.id

        # If no test selected (remaining probability goes to primary)
        logger.info(f"Selected primary URL for IP hash {hash_float:.4f}")
        return primary_url, None
