from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
