from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Integer,
    String,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.form_entry import FormEntry


class GoogleForm(Base):
    """New google_forms table (CRUD allowed)"""

    __tablename__ = "google_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        unique=True,
    )
    responder_form_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        unique=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    entries: Mapped[List["FormEntry"]] = relationship(
        "FormEntry",
        back_populates="google_form",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
