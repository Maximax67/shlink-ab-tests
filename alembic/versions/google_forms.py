"""
Create google_forms table

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create google_forms table"""
    op.create_table(
        "google_forms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("form_id", sa.String(length=128), nullable=False),
        sa.Column("responder_form_id", sa.String(length=128), nullable=False),
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
        sa.UniqueConstraint("form_id", name="uq_google_forms_form_id"),
        sa.UniqueConstraint(
            "responder_form_id", name="uq_google_forms_responder_form_id"
        ),
    )

    # Indexes
    op.create_index("idx_google_forms_form_id", "google_forms", ["form_id"])
    op.create_index(
        "idx_google_forms_responder_form_id",
        "google_forms",
        ["responder_form_id"],
    )


def downgrade() -> None:
    """Drop google_forms table"""
    op.drop_index("idx_google_forms_responder_form_id", table_name="google_forms")
    op.drop_index("idx_google_forms_form_id", table_name="google_forms")
    op.drop_table("google_forms")
