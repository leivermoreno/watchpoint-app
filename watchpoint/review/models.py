from typing import List
from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..db import db


class Review(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str]
    stars: Mapped[int]
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(True), default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="reviews")
    title: Mapped["Title"] = relationship()
    votes: Mapped[List["Vote"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    __table_args__ = (
        UniqueConstraint("title_id", "user_id", name="title_user_review_uc"),
        CheckConstraint("stars BETWEEN 1 AND 5", name="review_stars_range"),
    )


class Vote(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    upvote: Mapped[bool]
    review_id: Mapped[int] = mapped_column(ForeignKey("review.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="review_vote_uc"),)
