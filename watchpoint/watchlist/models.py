from sqlalchemy import ForeignKey, Enum, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import db

WATCHLIST_CHOICES = ("pending", "completed", "favorites")


class Watchlist(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    list: Mapped[str] = mapped_column(Enum(*WATCHLIST_CHOICES, name="watchlist_enum"))
    title: Mapped["Title"] = relationship(lazy="joined")
    __table_args__ = (UniqueConstraint("title_id", "user_id", name="title_user_uc"),)

    @staticmethod
    def get_by_user(user_id, list):
        stmt = select(Watchlist).filter_by(user_id=user_id)
        if list in WATCHLIST_CHOICES:
            stmt = stmt.filter_by(list=list)

        return db.session.scalars(stmt)

    @staticmethod
    def upsert_watchlist(user_id, title_id, watchlist):
        stmt = (
            insert(Watchlist)
            .values(title_id=title_id, user_id=user_id, list=watchlist)
            .on_conflict_do_update(
                constraint="title_user_uc", set_=dict(list=watchlist)
            )
        )
        db.session.execute(stmt)
        db.session.commit()
