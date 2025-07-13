from sqlalchemy import JSON, ForeignKey, Enum, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column
from flask import g
from db import db


class Title(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)

    @property
    def watchlist(self):
        if not g.user:
            return
        stmt = select(Watchlist).where(
            Watchlist.title_id == self.id, Watchlist.user_id == g.user.id
        )
        return db.session.scalar(stmt)


class Watchlist(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    list: Mapped[str] = mapped_column(
        Enum("pending", "completed", "favorites", name="watchlist_enum")
    )
    __table_args__ = (UniqueConstraint("title_id", "user_id", name="title_user_uc"),)

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
