"""
Add title column to google_forms table

Revision ID: 003
Revises: 002
Create Date: 2026-01-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add title column to google_forms table
    """

    op.add_column(
        "google_forms",
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            server_default="",  # temporary default for existing rows
        ),
    )

    op.alter_column(
        "google_forms",
        "title",
        server_default=None,
    )


def downgrade() -> None:
    """
    Remove title column from google_forms table
    """
    op.drop_column("google_forms", "title")
