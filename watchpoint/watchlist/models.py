from sqlalchemy import ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import db

WATCHLIST_CHOICES = ("pending", "completed", "favorites")


class Watchlist(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    list: Mapped[str] = mapped_column(Enum(*WATCHLIST_CHOICES, name="watchlist_enum"))
    title: Mapped["Title"] = relationship()
    __table_args__ = (UniqueConstraint("title_id", "user_id", name="title_user_uc"),)
