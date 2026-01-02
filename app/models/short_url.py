from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import parse_qs, urlparse

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

from app.services.url_builder import UrlBuilder
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

    @property
    def redirect_url(self) -> Optional[str]:
        """Extract the redirect-url from the original_url query parameter."""
        try:
            parsed = urlparse(self.original_url)
            query_params = parse_qs(parsed.query)

            redirect_url = query_params.get("url", [None])[0]
            if redirect_url is None:
                return None

            del query_params["url"]

            string_params: Dict[str, str] = {}

            for param, value in query_params.items():
                string_params[param] = value[0] if len(value) == 1 else str(value)

            return UrlBuilder.build_url(
                redirect_url,
                True,
                string_params,
                None,
                False,
            )
        except Exception:
            return None
