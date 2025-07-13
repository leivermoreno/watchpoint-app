from sqlalchemy import ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from db import db


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
