"""add title search cache

Revision ID: 2b7c9d4e1f03
Revises: 8c4bc4124a33
Create Date: 2026-06-19 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2b7c9d4e1f03"
down_revision = "8c4bc4124a33"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "title_search_cache",
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("query"),
    )


def downgrade():
    op.drop_table("title_search_cache")
