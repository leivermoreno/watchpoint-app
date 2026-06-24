"""initial schema

Revision ID: 8c4bc4124a33
Revises:
Create Date: 2026-06-17 19:27:50.040507

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c4bc4124a33"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "title",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("poster_large", sa.String(), nullable=True),
        sa.Column("plot_overview", sa.String(), nullable=True),
        sa.Column("user_rating", sa.Float(), nullable=True),
        sa.Column("critic_score", sa.Float(), nullable=True),
        sa.Column("trailer", sa.String(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_title_name", "title", ["name"], unique=False)
    op.create_index("ix_title_type", "title", ["type"], unique=False)
    op.create_index("ix_title_year", "title", ["year"], unique=False)

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nickname"),
    )

    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stars BETWEEN 1 AND 5", name="review_stars_range"),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title_id", "user_id", name="title_user_review_uc"),
    )
    op.create_index("ix_review_created_at", "review", ["created_at"], unique=False)

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "favorites",
                name="watchlist_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title_id", "user_id", name="title_user_watchlist_uc"),
    )
    op.create_index("ix_watchlist_user_id", "watchlist", ["user_id"], unique=False)

    op.create_table(
        "vote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("upvote", sa.Boolean(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", "user_id", name="review_vote_uc"),
    )


def downgrade():
    op.drop_table("vote")
    op.drop_index("ix_watchlist_user_id", table_name="watchlist")
    op.drop_table("watchlist")
    op.drop_index("ix_review_created_at", table_name="review")
    op.drop_table("review")
    op.drop_table("user")
    op.drop_index("ix_title_year", table_name="title")
    op.drop_index("ix_title_type", table_name="title")
    op.drop_index("ix_title_name", table_name="title")
    op.drop_table("title")
