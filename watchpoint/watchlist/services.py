from flask import g
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from ..db import db
from .models import Watchlist, WATCHLIST_CHOICES


def get_watchlist_by_user(status=None):
    stmt = select(Watchlist).filter_by(user_id=g.user.id)
    if status in WATCHLIST_CHOICES:
        stmt = stmt.filter_by(status=status)

    stmt = stmt.join(Watchlist.title)

    return db.session.scalars(stmt)


def get_title_list_by_user(title_id):
    stmt = select(Watchlist).filter_by(title_id=title_id, user_id=g.user.id)
    return db.session.scalar(stmt)


def upsert_watchlist(title_id, status):
    stmt = (
        insert(Watchlist)
        .values(title_id=title_id, user_id=g.user.id, status=status)
        .on_conflict_do_update(
            constraint="title_user_watchlist_uc", set_=dict(status=status)
        )
    )
    db.session.execute(stmt)
    db.session.commit()
