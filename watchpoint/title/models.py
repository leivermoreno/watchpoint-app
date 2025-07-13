from sqlalchemy import JSON, select
from sqlalchemy.orm import Mapped, mapped_column
from flask import g
from db import db
from watchlist.models import Watchlist


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
