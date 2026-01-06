from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.google_form import GoogleForm


class FormEntry(Base):
    """Google Form entries table (CRUD allowed)"""

    __tablename__ = "form_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    google_form_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("google_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    google_form: Mapped["GoogleForm"] = relationship(
        "GoogleForm",
        back_populates="entries",
    )

    __table_args__ = (
        UniqueConstraint(
            "google_form_id",
            "entry_id",
            name="uq_form_entry_per_form",
        ),
    )
