"""
Create form_entries table

Revision ID: 004
Revises: 003
Create Date: 2026-01-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    form_entry_id_type = sa.BigInteger().with_variant(
        BIGINT(unsigned=True),
        "mysql",
    )

    op.create_table(
        "form_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("google_form_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", form_entry_id_type, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["google_form_id"],
            ["google_forms.id"],
            ondelete="CASCADE",
            name="fk_form_entries_google_form_id",
        ),
        sa.UniqueConstraint(
            "google_form_id",
            "entry_id",
            name="uq_form_entries_google_form_entry",
        ),
    )

    op.create_index(
        "idx_form_entries_google_form_id",
        "form_entries",
        ["google_form_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_form_entries_google_form_id",
        table_name="form_entries",
    )
    op.drop_table("form_entries")
