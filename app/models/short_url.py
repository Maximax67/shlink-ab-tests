from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .visit import Visit
    from .ab_test import ABTest


class ShortUrl(Base):
    """Existing short_urls table (READ-ONLY)"""

    __tablename__ = "short_urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    short_code: Mapped[str] = mapped_column(String(255), nullable=False)
    date_created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_since: Mapped[Optional[datetime]] = mapped_column(DateTime)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    max_visits: Mapped[Optional[int]] = mapped_column(Integer)
    import_source: Mapped[Optional[str]] = mapped_column(String(255))
    import_original_short_code: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[Optional[str]] = mapped_column(String(512))
    title_was_auto_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    crawlable: Mapped[bool] = mapped_column(Boolean, default=False)
    forward_query: Mapped[bool] = mapped_column(Boolean, default=True)
    domain_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    author_api_key_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Relationships
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="short_url")
    ab_tests: Mapped[list["ABTest"]] = relationship(
        "ABTest", back_populates="short_url"
    )

    __table_args__ = (
        Index("unique_short_code_plus_domain", "short_code", "domain_id", unique=True),
        Index("IDX_4A53F934115F0EE5", "domain_id"),
        Index("IDX_4A53F934C9EA6E08", "author_api_key_id"),
    )
