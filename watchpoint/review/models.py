from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import TimestampMixin, db

if TYPE_CHECKING:
    from ..auth.models import User
    from ..title.models import Title


class Review(TimestampMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str] = mapped_column(String(2000))
    stars: Mapped[int]
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(back_populates="reviews")
    title: Mapped["Title"] = relationship()
    votes: Mapped[list["Vote"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    __table_args__ = (
        UniqueConstraint("title_id", "user_id", name="title_user_review_uc"),
        CheckConstraint("stars BETWEEN 1 AND 5", name="review_stars_range"),
        Index("ix_review_created_at", "created_at"),  # backs the newest/oldest sort
    )


class Vote(TimestampMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    upvote: Mapped[bool]
    review_id: Mapped[int] = mapped_column(ForeignKey("review.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="review_vote_uc"),)
