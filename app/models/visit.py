from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .short_url import ShortUrl
    from .visit_location import VisitLocation


class Visit(Base):
    """Existing visits table (READ-ONLY)"""

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    referer: Mapped[Optional[str]] = mapped_column(String(1024))
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    remote_addr: Mapped[Optional[str]] = mapped_column(String(256))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    visited_url: Mapped[Optional[str]] = mapped_column(String(2048))
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    potential_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    redirect_url: Mapped[Optional[str]] = mapped_column(String(2048))
    short_url_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("short_urls.id", ondelete="CASCADE")
    )
    visit_location_id: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Relationships
    short_url: Mapped[Optional["ShortUrl"]] = relationship(
        "ShortUrl", back_populates="visits"
    )
    location: Mapped[Optional["VisitLocation"]] = relationship(
        "VisitLocation", back_populates="visit"
    )

    __table_args__ = (
        Index("IDX_444839EAF1252BC8", "short_url_id"),
        Index("IDX_444839EA8297882E", "visit_location_id"),
        Index("IDX_visits_date", "date"),
        Index("visits_potential_bot_IDX", "potential_bot"),
    )
