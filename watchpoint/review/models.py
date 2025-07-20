from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db import db


class Review(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str]
    stars: Mapped[int]
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(True), default=datetime.now, onupdate=datetime.now
    )
    user: Mapped["User"] = relationship()
    title: Mapped["Title"] = relationship()
    __table_args__ = (
        UniqueConstraint("title_id", "user_id", name="title_user_review_uc"),
    )
