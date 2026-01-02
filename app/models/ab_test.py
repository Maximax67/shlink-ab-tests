from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Integer,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .short_url import ShortUrl


class ABTest(Base):
    """New ab_tests table (CRUD allowed)"""

    __tablename__ = "ab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    short_url_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("short_urls.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    short_url: Mapped["ShortUrl"] = relationship("ShortUrl", back_populates="ab_tests")

    __table_args__ = (
        Index("idx_ab_tests_short_url", "short_url_id"),
        Index("idx_ab_tests_active", "is_active"),
        CheckConstraint(
            "probability >= 0.0 AND probability <= 1.0",
            name="chk_probability_range",
        ),
    )
