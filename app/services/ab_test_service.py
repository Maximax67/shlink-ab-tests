"""
Service for A/B test CRUD operations
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import ABTest, ShortUrl
from app.schemas import ABTestCreate, ABTestUpdate

logger = logging.getLogger(__name__)


class ABTestValidationError(Exception):
    """Raised when A/B test validation fails"""

    pass


class ABTestService:
    """Handles A/B test CRUD operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_tests(self, short_url_id: int) -> list[ABTest]:
        """Get all A/B tests for a short URL"""
        query = (
            select(ABTest)
            .where(ABTest.short_url_id == short_url_id)
            .order_by(ABTest.created_at)
        )
        return list(self.db.execute(query).scalars().all())

    def get_test_by_id(self, test_id: int) -> Optional[ABTest]:
        """Get A/B test by ID"""
        return self.db.get(ABTest, test_id)

    def calculate_total_probability(
        self, short_url_id: int, exclude_test_id: Optional[int] = None
    ) -> float:
        """
        Calculate total probability for all active tests

        Args:
            short_url_id: ID of the short URL
            exclude_test_id: Optional test ID to exclude from calculation

        Returns:
            Total probability (0.0 to 1.0)
        """
        query = (
            select(func.sum(ABTest.probability))
            .where(ABTest.short_url_id == short_url_id)
            .where(ABTest.is_active.is_(True))
        )

        if exclude_test_id:
            query = query.where(ABTest.id != exclude_test_id)

        result = self.db.execute(query).scalar()
        return float(result) if result else 0.0

    def validate_probability_sum(
        self,
        short_url_id: int,
        new_probability: float,
        exclude_test_id: Optional[int] = None,
    ) -> None:
        """
        Validate that total probability doesn't exceed 1.0

        Raises:
            ABTestValidationError: If validation fails
        """
        current_total = self.calculate_total_probability(short_url_id, exclude_test_id)
        new_total = current_total + new_probability

        if new_total > 1.0:
            raise ABTestValidationError(
                f"Total probability would be {new_total:.2f} (max 1.0). "
                f"Current total: {current_total:.2f}, attempting to add: {new_probability:.2f}"
            )

    def create_test(self, short_url_id: int, test_data: ABTestCreate) -> ABTest:
        """
        Create a new A/B test

        Args:
            short_url_id: ID of the short URL
            test_data: A/B test data

        Returns:
            Created ABTest object

        Raises:
            ABTestValidationError: If validation fails
        """
        # Verify short URL exists
        short_url = self.db.get(ShortUrl, short_url_id)
        if not short_url:
            raise ABTestValidationError(f"Short URL {short_url_id} not found")

        # Validate probability sum
        if test_data.is_active:
            self.validate_probability_sum(short_url_id, test_data.probability)

        # Create test
        ab_test = ABTest(
            short_url_id=short_url_id,
            target_url=test_data.target_url,
            probability=test_data.probability,
            is_active=test_data.is_active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        try:
            self.db.add(ab_test)
            self.db.commit()
            self.db.refresh(ab_test)

            logger.info(
                f"Created A/B test {ab_test.id} for short_url_id={short_url_id}"
            )
            return ab_test
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create A/B test: {e}")
            raise ABTestValidationError("Failed to create A/B test") from e

    def update_test(self, test_id: int, test_data: ABTestUpdate) -> ABTest:
        """
        Update an existing A/B test

        Args:
            test_id: ID of the test to update
            test_data: Updated test data

        Returns:
            Updated ABTest object

        Raises:
            ABTestValidationError: If validation fails or test not found
        """
        ab_test = self.get_test_by_id(test_id)
        if not ab_test:
            raise ABTestValidationError(f"A/B test {test_id} not found")

        # Validate probability if being changed
        if test_data.probability is not None:
            # Check if becoming active or already active
            will_be_active = (
                test_data.is_active
                if test_data.is_active is not None
                else ab_test.is_active
            )

            if will_be_active:
                self.validate_probability_sum(
                    ab_test.short_url_id, test_data.probability, exclude_test_id=test_id
                )

        # Update fields
        if test_data.target_url is not None:
            ab_test.target_url = test_data.target_url

        if test_data.probability is not None:
            ab_test.probability = test_data.probability

        if test_data.is_active is not None:
            # If activating, validate probability
            if test_data.is_active and not ab_test.is_active:
                self.validate_probability_sum(
                    ab_test.short_url_id, ab_test.probability, exclude_test_id=test_id
                )
            ab_test.is_active = test_data.is_active

        ab_test.updated_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
            self.db.refresh(ab_test)

            logger.info(f"Updated A/B test {test_id}")
            return ab_test
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update A/B test: {e}")
            raise ABTestValidationError("Failed to update A/B test") from e

    def delete_test(self, test_id: int) -> bool:
        """
        Delete an A/B test

        Args:
            test_id: ID of the test to delete

        Returns:
            True if deleted, False if not found
        """
        ab_test = self.get_test_by_id(test_id)
        if not ab_test:
            return False

        self.db.delete(ab_test)
        self.db.commit()

        logger.info(f"Deleted A/B test {test_id}")
        return True
