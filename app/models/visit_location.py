from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Double, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .visit import Visit


class VisitLocation(Base):
    """Visit locations table (Read Only)"""

    __tablename__ = "visit_locations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("visits.id", ondelete="CASCADE"),
        primary_key=True,
    )
    country_code: Mapped[Optional[str]] = mapped_column(String(255))
    country_name: Mapped[Optional[str]] = mapped_column(String(255))
    region_name: Mapped[Optional[str]] = mapped_column(String(255))
    city_name: Mapped[Optional[str]] = mapped_column(String(255))
    timezone: Mapped[Optional[str]] = mapped_column(String(255))
    lat: Mapped[float] = mapped_column(Double(), nullable=False)
    lon: Mapped[float] = mapped_column(Double(), nullable=False)
    is_empty: Mapped[bool] = mapped_column(nullable=False, default=False)

    visit: Mapped[Optional["Visit"]] = relationship("Visit", back_populates="location")
