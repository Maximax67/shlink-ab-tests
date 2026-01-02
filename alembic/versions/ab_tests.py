"""
Create ab_tests table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ab_tests table"""
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("short_url_id", BIGINT(unsigned=True), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["short_url_id"], ["short_urls.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "probability >= 0.0 AND probability <= 1.0", name="chk_probability_range"
        ),
    )

    # Create indexes
    op.create_index("idx_ab_tests_short_url", "ab_tests", ["short_url_id"])
    op.create_index("idx_ab_tests_active", "ab_tests", ["is_active"])


def downgrade() -> None:
    """Drop ab_tests table"""
    op.drop_index("idx_ab_tests_active", table_name="ab_tests")
    op.drop_index("idx_ab_tests_short_url", table_name="ab_tests")
    op.drop_table("ab_tests")
